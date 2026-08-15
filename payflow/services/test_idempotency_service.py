import threading
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db import connections
from django.urls import reverse
from rest_framework.test import APIClient
from decimal import Decimal

from idempotency.models import IdempotencyKey
from payments.models import Payment
from services.idempotency_service import IdempotencyKeyInProgress, IdempotencyService

User = get_user_model()


@pytest.mark.django_db
class TestIdempotencyServiceBasics:
    def test_same_user_same_key_returns_same_record(self):
        user = User.objects.create_user(username="u1", password="pass")

        record, is_new = IdempotencyService.create_record(
            user, "key-1", "/x", "POST"
        )
        assert is_new is True

        IdempotencyService.save_response(record, {"ok": True}, 201)

        cached = IdempotencyService.get_existing_response(user, "key-1", "/x", "POST")
        assert cached == ({"ok": True}, 201)

    def test_same_key_different_user_is_isolated(self):
        """
        La misma Idempotency-Key usada por otro usuario nunca debe poder
        leer ni reutilizar el registro del primero.
        """
        user_a = User.objects.create_user(username="a", password="pass")
        user_b = User.objects.create_user(username="b", password="pass")

        record_a, is_new_a = IdempotencyService.create_record(
            user_a, "shared-key", "/x", "POST"
        )
        IdempotencyService.save_response(record_a, {"owner": "a"}, 201)

        # user_b nunca ve la respuesta de user_a.
        assert IdempotencyService.get_existing_response(user_b, "shared-key", "/x", "POST") is None

        # user_b puede crear su propio registro independiente con la misma key.
        record_b, is_new_b = IdempotencyService.create_record(
            user_b, "shared-key", "/x", "POST"
        )
        assert is_new_b is True
        assert record_b.id != record_a.id

    def test_same_key_different_endpoint_conflicts(self):
        user = User.objects.create_user(username="u1", password="pass")

        record, _ = IdempotencyService.create_record(user, "key-1", "/x", "POST")
        IdempotencyService.save_response(record, {"ok": True}, 201)

        with pytest.raises(ValueError):
            IdempotencyService.get_existing_response(user, "key-1", "/y", "POST")

        with pytest.raises(ValueError):
            IdempotencyService.create_record(user, "key-1", "/y", "POST")

    def test_processing_record_reports_in_progress_not_a_cached_response(self):
        user = User.objects.create_user(username="u1", password="pass")

        # Se crea pero nunca se completa (simula una operación en curso).
        IdempotencyService.create_record(user, "key-1", "/x", "POST")

        assert IdempotencyService.get_existing_response(user, "key-1", "/x", "POST") is None

        with pytest.raises(IdempotencyKeyInProgress):
            IdempotencyService.create_record(user, "key-1", "/x", "POST")

    def test_discard_record_allows_clean_retry_after_transient_failure(self):
        user = User.objects.create_user(username="u1", password="pass")

        record, _ = IdempotencyService.create_record(user, "key-1", "/x", "POST")
        IdempotencyService.discard_record(record)

        assert IdempotencyKey.objects.filter(user=user, key="key-1").count() == 0

        # Un reintento legítimo puede volver a arrancar de cero.
        record2, is_new = IdempotencyService.create_record(user, "key-1", "/x", "POST")
        assert is_new is True

    def test_deterministic_business_failure_is_cached_as_failed(self):
        user = User.objects.create_user(username="u1", password="pass")

        record, _ = IdempotencyService.create_record(user, "key-1", "/x", "POST")
        IdempotencyService.save_response(record, {"error": "Insufficient balance"}, 400)

        record.refresh_from_db()
        assert record.status == IdempotencyKey.STATUS_FAILED

        cached = IdempotencyService.get_existing_response(user, "key-1", "/x", "POST")
        assert cached == ({"error": "Insufficient balance"}, 400)


@pytest.mark.django_db(transaction=True)
@mock.patch("services.payment_service.payment_completed_event")
def test_concurrent_requests_same_key_execute_payment_exactly_once(mock_event):
    """
    Dos requests HTTP concurrentes con la MISMA Idempotency-Key deben
    producir exactamente un Payment, y ambas respuestas deben referirse
    a esa misma operación (o una de ellas debe recibir 409 si llegó a
    la carrera mientras la otra seguía en PROCESSING).

    payment_completed_event se mockea porque dispara tasks de Celery
    (.delay()) que necesitan un broker real corriendo; no es parte de lo
    que este test verifica.
    """
    sender = User.objects.create_user(username="sender_c", password="pass")
    receiver = User.objects.create_user(username="receiver_c", password="pass")

    sender.wallet.balance = Decimal("100.00")
    sender.wallet.save(update_fields=["balance"])

    url = reverse("create-payment")
    results = []

    def make_request():
        client = APIClient()
        client.force_authenticate(sender)
        response = client.post(
            url,
            {"receiver_username": receiver.username, "amount": "10.00"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="same-key-concurrent",
        )
        results.append(response)
        connections.close_all()

    t1 = threading.Thread(target=make_request)
    t2 = threading.Thread(target=make_request)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert Payment.objects.count() == 1

    # Cada respuesta es 201 (si llegó a leer el resultado final) o 409
    # (si llegó justo mientras la otra todavía estaba en PROCESSING).
    # Nunca ambas 201 con Payment distinto, y nunca una 500.
    statuses = sorted(r.status_code for r in results)
    assert statuses[0] in (201, 409)
    assert statuses[1] in (201, 409)
    assert 201 in statuses

    payment_ids = {
        r.data["id"] for r in results if r.status_code == 201 and "id" in r.data
    }
    assert len(payment_ids) == 1
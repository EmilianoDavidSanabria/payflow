import pytest
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from payments.models import Payment, PaymentRequest
from ledger.models import LedgerEntry
from audit.models import AuditLog

User = get_user_model()

@pytest.mark.django_db
def test_payment_request_detail_allows_requester():
    requester = User.objects.create_user(username="detail_requester_user", password="pass")
    requested_from = User.objects.create_user(username="detail_requested_from_user", password="pass")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("16.00"),
    )

    client = APIClient()
    client.force_authenticate(requester)

    response = client.get(
        reverse("payment-request-detail", kwargs={"request_id": payment_request.id})
    )

    assert response.status_code == 200
    assert response.data["id"] == payment_request.id
    assert response.data["requester_username"] == requester.username
    assert response.data["requested_from_username"] == requested_from.username
    assert response.data["direction"] == "outgoing"


@pytest.mark.django_db
def test_payment_request_detail_allows_requested_from_user():
    requester = User.objects.create_user(username="detail_requester_2", password="pass")
    requested_from = User.objects.create_user(username="detail_requested_from_2", password="pass")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("21.00"),
    )

    client = APIClient()
    client.force_authenticate(requested_from)

    response = client.get(
        reverse("payment-request-detail", kwargs={"request_id": payment_request.id})
    )

    assert response.status_code == 200
    assert response.data["id"] == payment_request.id
    assert response.data["direction"] == "incoming"
    assert response.data["counterparty_username"] == requester.username


@pytest.mark.django_db
def test_payment_request_detail_rejects_stranger():
    requester = User.objects.create_user(username="detail_perm_requester", password="pass")
    requested_from = User.objects.create_user(username="detail_perm_requested_from", password="pass")
    stranger = User.objects.create_user(username="detail_perm_stranger", password="pass")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("13.00"),
    )

    client = APIClient()
    client.force_authenticate(stranger)

    response = client.get(
        reverse("payment-request-detail", kwargs={"request_id": payment_request.id})
    )

    assert response.status_code == 403
    assert response.data["error"] == "Not authorized"


@pytest.mark.django_db
def test_payment_request_detail_returns_accepted_payment_id_when_present():
    requester = User.objects.create_user(username="detail_accept_requester", password="pass")
    requested_from = User.objects.create_user(username="detail_accept_requested_from", password="pass")

    requester.wallet.balance = Decimal("0.00")
    requester.wallet.save(update_fields=["balance"])

    requested_from.wallet.balance = Decimal("100.00")
    requested_from.wallet.save(update_fields=["balance"])

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("25.00"),
    )

    client = APIClient()
    client.force_authenticate(requested_from)

    accept_response = client.post(
        reverse("accept-payment-request", kwargs={"request_id": payment_request.id}),
        format="json",
    )

    assert accept_response.status_code == 200

    detail_response = client.get(
        reverse("payment-request-detail", kwargs={"request_id": payment_request.id})
    )

    assert detail_response.status_code == 200
    assert detail_response.data["status"] == "ACCEPTED"
    assert detail_response.data["accepted_payment_id"] is not None


@pytest.mark.django_db
def test_payment_request_detail_allows_requester():
    requester = User.objects.create_user(username="request_detail_requester", password="pass")
    requested_from = User.objects.create_user(username="request_detail_payer", password="pass")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("25.00"),
    )

    client = APIClient()
    client.force_authenticate(requester)

    response = client.get(
        reverse("payment-request-detail", kwargs={"request_id": payment_request.id})
    )

    assert response.status_code == 200
    assert response.data["id"] == payment_request.id
    assert response.data["requester"] == requester.id
    assert response.data["requested_from"] == requested_from.id
    assert response.data["requester_username"] == requester.username
    assert response.data["requested_from_username"] == requested_from.username
    assert response.data["amount"] == "25.00"
    assert response.data["status"] == "PENDING"
    assert response.data["direction"] == "outgoing"
    assert response.data["counterparty_username"] == requested_from.username
    assert response.data["accepted_payment_id"] is None


@pytest.mark.django_db
def test_payment_request_detail_allows_requested_from():
    requester = User.objects.create_user(username="request_detail_requester_2", password="pass")
    requested_from = User.objects.create_user(username="request_detail_payer_2", password="pass")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("40.00"),
    )

    client = APIClient()
    client.force_authenticate(requested_from)

    response = client.get(
        reverse("payment-request-detail", kwargs={"request_id": payment_request.id})
    )

    assert response.status_code == 200
    assert response.data["id"] == payment_request.id
    assert response.data["direction"] == "incoming"
    assert response.data["counterparty_username"] == requester.username


@pytest.mark.django_db
def test_payment_request_detail_rejects_stranger():
    requester = User.objects.create_user(username="request_detail_requester_3", password="pass")
    requested_from = User.objects.create_user(username="request_detail_payer_3", password="pass")
    stranger = User.objects.create_user(username="request_detail_stranger", password="pass")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("18.00"),
    )

    client = APIClient()
    client.force_authenticate(stranger)

    response = client.get(
        reverse("payment-request-detail", kwargs={"request_id": payment_request.id})
    )

    assert response.status_code == 403
    assert response.data["error"] == "Not authorized"


@pytest.mark.django_db
def test_payment_request_detail_returns_404_when_not_found():
    user = User.objects.create_user(username="request_detail_missing_user", password="pass")

    client = APIClient()
    client.force_authenticate(user)

    response = client.get(
        reverse("payment-request-detail", kwargs={"request_id": 999999})
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_payment_request_detail_includes_linked_payment_when_accepted():
    requester = User.objects.create_user(username="request_detail_requester_4", password="pass")
    requested_from = User.objects.create_user(username="request_detail_payer_4", password="pass")

    requester.wallet.balance = Decimal("0.00")
    requester.wallet.save(update_fields=["balance"])

    requested_from.wallet.balance = Decimal("100.00")
    requested_from.wallet.save(update_fields=["balance"])

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("35.00"),
    )

    accepted_payment = Payment.objects.create(
        sender=requested_from,
        receiver=requester,
        amount=Decimal("35.00"),
        status="COMPLETED",
        idempotency_key="request-detail-linked-payment-1",
    )

    payment_request.status = "ACCEPTED"
    payment_request.accepted_payment = accepted_payment
    payment_request.save(update_fields=["status", "accepted_payment"])

    client = APIClient()
    client.force_authenticate(requester)

    response = client.get(
        reverse("payment-request-detail", kwargs={"request_id": payment_request.id})
    )

    assert response.status_code == 200
    assert response.data["status"] == "ACCEPTED"
    assert response.data["accepted_payment_id"] == accepted_payment.id


@pytest.mark.django_db
def test_payment_request_detail_contract_has_expected_keys():
    requester = User.objects.create_user(username="request_detail_contract_requester", password="pass")
    requested_from = User.objects.create_user(username="request_detail_contract_payer", password="pass")

    payment_request = PaymentRequest.objects.create(
        requester=requester,
        requested_from=requested_from,
        amount=Decimal("27.00"),
    )

    client = APIClient()
    client.force_authenticate(requester)

    response = client.get(
        reverse("payment-request-detail", kwargs={"request_id": payment_request.id})
    )

    assert response.status_code == 200
    assert set(response.data.keys()) == {
        "id",
        "requester",
        "requester_username",
        "requested_from",
        "requested_from_username",
        "amount",
        "status",
        "accepted_payment_id",
        "created_at",
        "updated_at",
        "resolved_at",
        "direction",
        "counterparty_username",
    }
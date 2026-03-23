import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from payments.models import Payment

User = get_user_model()


@pytest.mark.django_db
def test_payment_idempotency():
    sender = User.objects.create_user(username="u1", password="pass")
    receiver = User.objects.create_user(username="u2", password="pass")

    sender.wallet.balance = Decimal("100.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("0.00")
    receiver.wallet.save(update_fields=["balance"])

    client = APIClient()
    client.force_authenticate(sender)

    url = reverse("create-payment")

    headers = {"HTTP_IDEMPOTENCY_KEY": "abc123"}

    data = {
        "receiver_username": receiver.username,
        "amount": "10.00",
    }

    r1 = client.post(url, data, format="json", **headers)
    r2 = client.post(url, data, format="json", **headers)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.data["id"] == r2.data["id"]
    assert Payment.objects.count() == 1
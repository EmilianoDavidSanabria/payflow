import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_payment_flow():
    sender = User.objects.create_user(username="user1", password="pass")
    receiver = User.objects.create_user(username="user2", password="pass")

    sender.wallet.balance = Decimal("100.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("0.00")
    receiver.wallet.save(update_fields=["balance"])

    client = APIClient()
    client.force_authenticate(sender)

    response = client.post(
        "/payments/create/",
        {
            "receiver_username": receiver.username,
            "amount": "10.00",
        },
        format="json",
        HTTP_IDEMPOTENCY_KEY="abc123",
    )

    assert response.status_code == 201
    assert response.data["receiver_username"] == receiver.username
    assert response.data["amount"] == "10.00"
    assert response.data["status"] == "COMPLETED"
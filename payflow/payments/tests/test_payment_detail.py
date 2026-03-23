from decimal import Decimal

import pytest
from django.urls import reverse

from payments.models import Payment

from .helpers import authenticate_client, create_user


@pytest.mark.django_db
def test_payment_detail_allows_sender_or_receiver_only():
    sender = create_user("alice_detail", balance="100.00")
    receiver = create_user("bob_detail", balance="100.00")
    stranger = create_user("charlie_detail", balance="100.00")

    payment = Payment.objects.create(
        sender=sender,
        receiver=receiver,
        amount=Decimal("10.00"),
        status="COMPLETED",
        idempotency_key="detail-1",
    )

    url = reverse("payment-detail", kwargs={"payment_id": payment.id})

    sender_client = authenticate_client(sender)
    sender_response = sender_client.get(url)

    receiver_client = authenticate_client(receiver)
    receiver_response = receiver_client.get(url)

    stranger_client = authenticate_client(stranger)
    stranger_response = stranger_client.get(url)

    assert sender_response.status_code == 200
    assert receiver_response.status_code == 200
    assert stranger_response.status_code == 403
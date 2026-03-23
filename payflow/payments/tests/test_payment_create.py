from decimal import Decimal

import pytest
from django.urls import reverse

from payments.models import Payment
from ledger.models import LedgerEntry
from audit.models import AuditLog

from .helpers import authenticate_client, create_user


@pytest.mark.django_db
def test_create_payment_success():
    sender = create_user("alice", balance="100.00")
    receiver = create_user("bob", balance="20.00")

    client = authenticate_client(sender)

    url = reverse("create-payment")
    data = {
        "receiver_username": receiver.username,
        "amount": "10.00",
    }

    response = client.post(
        url,
        data,
        format="json",
        HTTP_IDEMPOTENCY_KEY="payment-success-1",
    )

    sender.wallet.refresh_from_db()
    receiver.wallet.refresh_from_db()

    payment = Payment.objects.get()

    assert response.status_code == 201
    assert payment.sender == sender
    assert payment.receiver == receiver
    assert payment.amount == Decimal("10.00")
    assert payment.status == "COMPLETED"

    assert sender.wallet.balance == Decimal("90.00")
    assert receiver.wallet.balance == Decimal("30.00")

    assert LedgerEntry.objects.filter(reference=f"payment_{payment.id}").count() == 2
    assert AuditLog.objects.filter(entity_type="payment", entity_id=payment.id).count() == 2
    assert AuditLog.objects.filter(action="WALLET_UPDATED").count() == 2


@pytest.mark.django_db
def test_create_payment_fails_with_insufficient_balance():
    sender = create_user("alice_insufficient", balance="5.00")
    receiver = create_user("bob_insufficient", balance="20.00")

    client = authenticate_client(sender)

    url = reverse("create-payment")
    data = {
        "receiver_username": receiver.username,
        "amount": "10.00",
    }

    response = client.post(
        url,
        data,
        format="json",
        HTTP_IDEMPOTENCY_KEY="insufficient-balance-1",
    )

    sender.wallet.refresh_from_db()
    receiver.wallet.refresh_from_db()

    assert response.status_code == 400
    assert Payment.objects.count() == 0
    assert LedgerEntry.objects.count() == 0
    assert AuditLog.objects.count() == 0
    assert sender.wallet.balance == Decimal("5.00")
    assert receiver.wallet.balance == Decimal("20.00")


@pytest.mark.django_db
def test_create_payment_rejects_self_payment():
    user = create_user("alice_self", balance="100.00")

    client = authenticate_client(user)

    url = reverse("create-payment")
    data = {
        "receiver_username": user.username,
        "amount": "10.00",
    }

    response = client.post(
        url,
        data,
        format="json",
        HTTP_IDEMPOTENCY_KEY="self-payment-1",
    )

    user.wallet.refresh_from_db()

    assert response.status_code == 400
    assert Payment.objects.count() == 0
    assert LedgerEntry.objects.count() == 0
    assert AuditLog.objects.count() == 0
    assert user.wallet.balance == Decimal("100.00")


@pytest.mark.django_db
def test_create_payment_rejects_invalid_amount():
    sender = create_user("alice_invalid", balance="100.00")
    receiver = create_user("bob_invalid", balance="0.00")

    client = authenticate_client(sender)

    url = reverse("create-payment")
    data = {
        "receiver_username": receiver.username,
        "amount": "0.00",
    }

    response = client.post(
        url,
        data,
        format="json",
        HTTP_IDEMPOTENCY_KEY="invalid-amount-1",
    )

    sender.wallet.refresh_from_db()
    receiver.wallet.refresh_from_db()

    assert response.status_code == 400
    assert Payment.objects.count() == 0
    assert LedgerEntry.objects.count() == 0
    assert AuditLog.objects.count() == 0
    assert sender.wallet.balance == Decimal("100.00")
    assert receiver.wallet.balance == Decimal("0.00")
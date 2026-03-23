import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model

from payments.models import Payment
from ledger.models import LedgerEntry
from audit.models import AuditLog
from services.payment_service import PaymentService
from core.exceptions import (
    InsufficientBalance,
    InvalidPaymentAmount,
    SelfPaymentNotAllowed,
)

User = get_user_model()


@pytest.mark.django_db
def test_payment_service_creates_completed_payment_and_updates_balances():
    sender = User.objects.create_user(username="svc_alice", password="pass")
    receiver = User.objects.create_user(username="svc_bob", password="pass")

    sender.wallet.balance = Decimal("100.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("25.00")
    receiver.wallet.save(update_fields=["balance"])

    payment = PaymentService.create_payment(
        sender=sender,
        receiver=receiver,
        amount=Decimal("10.00"),
        idempotency_key="svc-success-1",
    )

    sender.wallet.refresh_from_db()
    receiver.wallet.refresh_from_db()
    payment.refresh_from_db()

    assert payment.sender == sender
    assert payment.receiver == receiver
    assert payment.amount == Decimal("10.00")
    assert payment.status == "COMPLETED"

    assert sender.wallet.balance == Decimal("90.00")
    assert receiver.wallet.balance == Decimal("35.00")


@pytest.mark.django_db
def test_payment_service_creates_ledger_entries():
    sender = User.objects.create_user(username="svc_ledger_alice", password="pass")
    receiver = User.objects.create_user(username="svc_ledger_bob", password="pass")

    sender.wallet.balance = Decimal("100.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("0.00")
    receiver.wallet.save(update_fields=["balance"])

    payment = PaymentService.create_payment(
        sender=sender,
        receiver=receiver,
        amount=Decimal("15.00"),
        idempotency_key="svc-ledger-1",
    )

    reference = f"payment_{payment.id}"
    entries = LedgerEntry.objects.filter(reference=reference).order_by("id")

    assert entries.count() == 2

    debit_entry = entries[0]
    credit_entry = entries[1]

    assert debit_entry.user == sender
    assert debit_entry.debit == Decimal("15.00")
    assert debit_entry.credit == Decimal("0.00")

    assert credit_entry.user == receiver
    assert credit_entry.debit == Decimal("0.00")
    assert credit_entry.credit == Decimal("15.00")


@pytest.mark.django_db
def test_payment_service_creates_expected_audit_logs():
    sender = User.objects.create_user(username="svc_audit_alice", password="pass")
    receiver = User.objects.create_user(username="svc_audit_bob", password="pass")

    sender.wallet.balance = Decimal("80.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("20.00")
    receiver.wallet.save(update_fields=["balance"])

    payment = PaymentService.create_payment(
        sender=sender,
        receiver=receiver,
        amount=Decimal("10.00"),
        idempotency_key="svc-audit-1",
    )

    payment_logs = AuditLog.objects.filter(
        entity_type="payment",
        entity_id=payment.id
    ).order_by("id")

    wallet_logs = AuditLog.objects.filter(action="WALLET_UPDATED").order_by("id")

    assert payment_logs.count() == 2
    assert payment_logs[0].action == "PAYMENT_CREATED"
    assert payment_logs[1].action == "PAYMENT_COMPLETED"

    assert wallet_logs.count() == 2
    assert {log.user_id for log in wallet_logs} == {sender.id, receiver.id}


@pytest.mark.django_db
def test_payment_service_is_idempotent():
    sender = User.objects.create_user(username="svc_idem_alice", password="pass")
    receiver = User.objects.create_user(username="svc_idem_bob", password="pass")

    sender.wallet.balance = Decimal("100.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("5.00")
    receiver.wallet.save(update_fields=["balance"])

    payment_1 = PaymentService.create_payment(
        sender=sender,
        receiver=receiver,
        amount=Decimal("12.00"),
        idempotency_key="svc-idempotent-1",
    )

    payment_2 = PaymentService.create_payment(
        sender=sender,
        receiver=receiver,
        amount=Decimal("12.00"),
        idempotency_key="svc-idempotent-1",
    )

    sender.wallet.refresh_from_db()
    receiver.wallet.refresh_from_db()

    assert payment_1.id == payment_2.id
    assert Payment.objects.count() == 1
    assert sender.wallet.balance == Decimal("88.00")
    assert receiver.wallet.balance == Decimal("17.00")


@pytest.mark.django_db
def test_payment_service_rejects_self_payment():
    user = User.objects.create_user(username="svc_self_user", password="pass")

    user.wallet.balance = Decimal("100.00")
    user.wallet.save(update_fields=["balance"])

    with pytest.raises(SelfPaymentNotAllowed):
        PaymentService.create_payment(
            sender=user,
            receiver=user,
            amount=Decimal("10.00"),
            idempotency_key="svc-self-1",
        )

    user.wallet.refresh_from_db()

    assert Payment.objects.count() == 0
    assert LedgerEntry.objects.count() == 0
    assert AuditLog.objects.count() == 0
    assert user.wallet.balance == Decimal("100.00")


@pytest.mark.django_db
def test_payment_service_rejects_invalid_amount():
    sender = User.objects.create_user(username="svc_invalid_alice", password="pass")
    receiver = User.objects.create_user(username="svc_invalid_bob", password="pass")

    sender.wallet.balance = Decimal("100.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("0.00")
    receiver.wallet.save(update_fields=["balance"])

    with pytest.raises(InvalidPaymentAmount):
        PaymentService.create_payment(
            sender=sender,
            receiver=receiver,
            amount=Decimal("0.00"),
            idempotency_key="svc-invalid-1",
        )

    sender.wallet.refresh_from_db()
    receiver.wallet.refresh_from_db()

    assert Payment.objects.count() == 0
    assert LedgerEntry.objects.count() == 0
    assert AuditLog.objects.count() == 0
    assert sender.wallet.balance == Decimal("100.00")
    assert receiver.wallet.balance == Decimal("0.00")


@pytest.mark.django_db
def test_payment_service_rejects_insufficient_balance():
    sender = User.objects.create_user(username="svc_insufficient_alice", password="pass")
    receiver = User.objects.create_user(username="svc_insufficient_bob", password="pass")

    sender.wallet.balance = Decimal("3.00")
    sender.wallet.save(update_fields=["balance"])

    receiver.wallet.balance = Decimal("40.00")
    receiver.wallet.save(update_fields=["balance"])

    with pytest.raises(InsufficientBalance):
        PaymentService.create_payment(
            sender=sender,
            receiver=receiver,
            amount=Decimal("10.00"),
            idempotency_key="svc-insufficient-1",
        )

    sender.wallet.refresh_from_db()
    receiver.wallet.refresh_from_db()

    assert Payment.objects.count() == 0
    assert LedgerEntry.objects.count() == 0
    assert AuditLog.objects.count() == 0
    assert sender.wallet.balance == Decimal("3.00")
    assert receiver.wallet.balance == Decimal("40.00")
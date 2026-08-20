from decimal import Decimal

import pytest
from django.db import IntegrityError

from django.contrib.auth import get_user_model

from ledger.models import LedgerEntry
from services.ledger_service import LedgerService


@pytest.mark.django_db
def test_transfer_creates_exactly_one_debit_and_one_credit():
    User = get_user_model()

    sender = User.objects.create_user(
        username="ledger_sender",
        password="testpass123",
    )

    receiver = User.objects.create_user(
        username="ledger_receiver",
        password="testpass123",
    )

    reference = "ledger_test_transfer_1"

    LedgerService.transfer(
        sender=sender,
        receiver=receiver,
        amount=Decimal("100.00"),
        reference=reference,
    )

    entries = LedgerEntry.objects.filter(
        reference=reference
    ).order_by("id")

    assert entries.count() == 2

    assert entries[0].debit == Decimal("100.00")
    assert entries[0].credit == Decimal("0.00")

    assert entries[1].debit == Decimal("0.00")
    assert entries[1].credit == Decimal("100.00")


@pytest.mark.django_db
def test_ledger_entry_cannot_have_both_debit_and_credit():
    with pytest.raises(IntegrityError):
        LedgerEntry.objects.create(
            account_type="SYSTEM",
            debit=Decimal("100.00"),
            credit=Decimal("100.00"),
            reference="invalid_both_sides",
        )


@pytest.mark.django_db
def test_ledger_entry_cannot_have_both_amounts_zero():
    with pytest.raises(IntegrityError):
        LedgerEntry.objects.create(
            account_type="SYSTEM",
            debit=Decimal("0.00"),
            credit=Decimal("0.00"),
            reference="invalid_zero_amounts",
        )


@pytest.mark.django_db
def test_ledger_entry_cannot_have_negative_amount():
    with pytest.raises(IntegrityError):
        LedgerEntry.objects.create(
            account_type="SYSTEM",
            debit=Decimal("-100.00"),
            credit=Decimal("0.00"),
            reference="invalid_negative",
        )


@pytest.mark.django_db
def test_reference_can_have_only_one_debit():
    reference = "duplicate_debit_reference"

    LedgerEntry.objects.create(
        account_type="SYSTEM",
        debit=Decimal("100.00"),
        credit=Decimal("0.00"),
        reference=reference,
    )

    with pytest.raises(IntegrityError):
        LedgerEntry.objects.create(
            account_type="SYSTEM",
            debit=Decimal("50.00"),
            credit=Decimal("0.00"),
            reference=reference,
        )


@pytest.mark.django_db
def test_reference_can_have_only_one_credit():
    reference = "duplicate_credit_reference"

    LedgerEntry.objects.create(
        account_type="SYSTEM",
        debit=Decimal("100.00"),
        credit=Decimal("0.00"),
        reference="duplicate_credit_reference",
    )

    LedgerEntry.objects.create(
        account_type="SYSTEM",
        debit=Decimal("0.00"),
        credit=Decimal("100.00"),
        reference=reference,
    )

    with pytest.raises(IntegrityError):
        LedgerEntry.objects.create(
            account_type="SYSTEM",
            debit=Decimal("0.00"),
            credit=Decimal("50.00"),
            reference=reference,
        )


@pytest.mark.django_db
def test_verify_integrity_detects_balanced_ledger():
    reference = "balanced_ledger"

    LedgerEntry.objects.create(
        account_type="SYSTEM",
        debit=Decimal("100.00"),
        credit=Decimal("0.00"),
        reference=reference,
    )

    LedgerEntry.objects.create(
        account_type="SYSTEM",
        debit=Decimal("0.00"),
        credit=Decimal("100.00"),
        reference=reference,
    )

    assert LedgerService.verify_integrity(reference) is True
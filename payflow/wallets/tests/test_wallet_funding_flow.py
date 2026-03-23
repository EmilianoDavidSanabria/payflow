import pytest
from decimal import Decimal
from django.urls import reverse

from wallets.models import WalletTransaction
from ledger.models import LedgerEntry
from audit.models import AuditLog


@pytest.mark.django_db
def test_wallet_top_up_creates_completed_transaction_and_updates_balance(
    authenticated_client,
    wallet,
):
    response = authenticated_client.post(
        reverse("wallet-top-up"),
        {"amount": "100.00"},
        format="json",
    )

    wallet.refresh_from_db()

    assert response.status_code == 201
    assert response.data["transaction_type"] == "TOP_UP"
    assert response.data["amount"] == "100.00"
    assert response.data["status"] == "COMPLETED"
    assert response.data["rail"] == "SANDBOX"
    assert wallet.balance == Decimal("100.00")


@pytest.mark.django_db
def test_wallet_top_up_creates_balanced_ledger_entries(authenticated_client, wallet_user):
    response = authenticated_client.post(
        reverse("wallet-top-up"),
        {"amount": "75.00"},
        format="json",
    )

    transaction_id = response.data["id"]
    reference = f"wallet_transaction_{transaction_id}"

    entries = LedgerEntry.objects.filter(reference=reference).order_by("id")

    assert response.status_code == 201
    assert entries.count() == 2

    system_entry = entries[0]
    user_entry = entries[1]

    assert system_entry.account_type == "SYSTEM"
    assert system_entry.user is None
    assert system_entry.debit == Decimal("75.00")
    assert system_entry.credit == Decimal("0.00")

    assert user_entry.account_type == "USER"
    assert user_entry.user == wallet_user
    assert user_entry.debit == Decimal("0.00")
    assert user_entry.credit == Decimal("75.00")

    total_debit = sum(entry.debit for entry in entries)
    total_credit = sum(entry.credit for entry in entries)

    assert total_debit == total_credit == Decimal("75.00")


@pytest.mark.django_db
def test_wallet_top_up_creates_audit_logs(authenticated_client):
    response = authenticated_client.post(
        reverse("wallet-top-up"),
        {"amount": "40.00"},
        format="json",
    )

    transaction_id = response.data["id"]

    created_log = AuditLog.objects.filter(
        action="WALLET_TOP_UP_CREATED",
        entity_type="wallet_transaction",
        entity_id=transaction_id,
    ).first()

    completed_log = AuditLog.objects.filter(
        action="WALLET_TOP_UP_COMPLETED",
        entity_type="wallet_transaction",
        entity_id=transaction_id,
    ).first()

    wallet_updated_log = AuditLog.objects.filter(
        action="WALLET_UPDATED",
        entity_type="wallet",
    ).order_by("-id").first()

    assert response.status_code == 201
    assert created_log is not None
    assert completed_log is not None
    assert wallet_updated_log is not None
    assert wallet_updated_log.metadata["reason"] == "wallet_top_up_completed"


@pytest.mark.django_db
def test_wallet_top_up_rejects_invalid_amount(authenticated_client):
    response = authenticated_client.post(
        reverse("wallet-top-up"),
        {"amount": "0.00"},
        format="json",
    )

    assert response.status_code == 400
    assert "amount" in response.data


@pytest.mark.django_db
def test_wallet_withdrawal_creates_completed_transaction_and_updates_balance(
    authenticated_client,
    funded_wallet,
):
    response = authenticated_client.post(
        reverse("wallet-withdraw"),
        {"amount": "80.00"},
        format="json",
    )

    funded_wallet.refresh_from_db()

    assert response.status_code == 201
    assert response.data["transaction_type"] == "WITHDRAWAL"
    assert response.data["amount"] == "80.00"
    assert response.data["status"] == "COMPLETED"
    assert response.data["rail"] == "SANDBOX"
    assert funded_wallet.balance == Decimal("120.00")


@pytest.mark.django_db
def test_wallet_withdrawal_creates_balanced_ledger_entries(authenticated_client, funded_wallet, wallet_user):
    response = authenticated_client.post(
        reverse("wallet-withdraw"),
        {"amount": "50.00"},
        format="json",
    )

    transaction_id = response.data["id"]
    reference = f"wallet_transaction_{transaction_id}"

    entries = LedgerEntry.objects.filter(reference=reference).order_by("id")

    assert response.status_code == 201
    assert entries.count() == 2

    user_entry = entries[0]
    system_entry = entries[1]

    assert user_entry.account_type == "USER"
    assert user_entry.user == wallet_user
    assert user_entry.debit == Decimal("50.00")
    assert user_entry.credit == Decimal("0.00")

    assert system_entry.account_type == "SYSTEM"
    assert system_entry.user is None
    assert system_entry.debit == Decimal("0.00")
    assert system_entry.credit == Decimal("50.00")

    total_debit = sum(entry.debit for entry in entries)
    total_credit = sum(entry.credit for entry in entries)

    assert total_debit == total_credit == Decimal("50.00")


@pytest.mark.django_db
def test_wallet_withdrawal_creates_audit_logs(authenticated_client, funded_wallet):
    response = authenticated_client.post(
        reverse("wallet-withdraw"),
        {"amount": "20.00"},
        format="json",
    )

    transaction_id = response.data["id"]

    created_log = AuditLog.objects.filter(
        action="WALLET_WITHDRAWAL_CREATED",
        entity_type="wallet_transaction",
        entity_id=transaction_id,
    ).first()

    completed_log = AuditLog.objects.filter(
        action="WALLET_WITHDRAWAL_COMPLETED",
        entity_type="wallet_transaction",
        entity_id=transaction_id,
    ).first()

    wallet_updated_log = AuditLog.objects.filter(
        action="WALLET_UPDATED",
        entity_type="wallet",
    ).order_by("-id").first()

    assert response.status_code == 201
    assert created_log is not None
    assert completed_log is not None
    assert wallet_updated_log is not None
    assert wallet_updated_log.metadata["reason"] == "wallet_withdrawal"


@pytest.mark.django_db
def test_wallet_withdrawal_rejects_insufficient_balance(authenticated_client, wallet):
    response = authenticated_client.post(
        reverse("wallet-withdraw"),
        {"amount": "25.00"},
        format="json",
    )

    wallet.refresh_from_db()

    assert response.status_code == 400
    assert response.data["error"] == "Insufficient balance"
    assert wallet.balance == Decimal("0.00")
    assert WalletTransaction.objects.count() == 0


@pytest.mark.django_db
def test_wallet_withdrawal_rejects_invalid_amount(authenticated_client, funded_wallet):
    response = authenticated_client.post(
        reverse("wallet-withdraw"),
        {"amount": "-10.00"},
        format="json",
    )

    assert response.status_code == 400
    assert "amount" in response.data
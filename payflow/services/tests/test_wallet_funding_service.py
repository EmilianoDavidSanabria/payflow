import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from audit.models import AuditLog
from core.exceptions import (
    InsufficientBalance,
    InvalidWalletTransactionAmount,
    InvalidWalletTransactionOperation,
    WalletNotFound,
)
from ledger.models import LedgerEntry
from services.wallet_funding_service import WalletFundingService
from wallets.models import Wallet, WalletTransaction


def create_user_without_wallet(username="user_without_wallet"):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="testpass123",
    )
    Wallet.objects.filter(user=user).delete()
    return user


@pytest.mark.django_db
def test_create_top_up_intent_creates_pending_transaction_and_audit_log(wallet_user, wallet):
    transaction = WalletFundingService.create_top_up_intent(
        user=wallet_user,
        amount=Decimal("120.00"),
        rail="MERCADO_PAGO",
        external_reference="ext_123",
        provider_status="CHECKOUT_CREATED",
    )

    wallet.refresh_from_db()

    assert transaction.transaction_type == "TOP_UP"
    assert transaction.amount == Decimal("120.00")
    assert transaction.status == "PENDING"
    assert transaction.rail == "MERCADO_PAGO"
    assert transaction.external_reference == "ext_123"
    assert transaction.provider_status == "CHECKOUT_CREATED"
    assert wallet.balance == Decimal("0.00")

    audit_log = AuditLog.objects.get(
        action="WALLET_TOP_UP_CREATED",
        entity_type="wallet_transaction",
        entity_id=transaction.id,
    )
    assert audit_log.metadata["wallet_id"] == wallet.id
    assert audit_log.metadata["amount"] == "120.00"
    assert audit_log.metadata["rail"] == "MERCADO_PAGO"
    assert audit_log.metadata["status"] == "PENDING"
    assert audit_log.metadata["provider_status"] == "CHECKOUT_CREATED"
    assert audit_log.metadata["external_reference"] == "ext_123"


@pytest.mark.django_db
def test_create_top_up_intent_rejects_invalid_amount(wallet_user):
    with pytest.raises(InvalidWalletTransactionAmount):
        WalletFundingService.create_top_up_intent(
            user=wallet_user,
            amount=Decimal("0.00"),
        )


@pytest.mark.django_db
def test_create_top_up_intent_raises_when_wallet_does_not_exist():
    user = create_user_without_wallet()

    with pytest.raises(WalletNotFound, match="Wallet not found for this user"):
        WalletFundingService.create_top_up_intent(
            user=user,
            amount=Decimal("50.00"),
        )


@pytest.mark.django_db
def test_complete_top_up_completes_pending_transaction_and_creates_ledger_and_audit(wallet_user, wallet):
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("150.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="old_ref",
        provider_status="CHECKOUT_CREATED",
    )

    completed = WalletFundingService.complete_top_up(
        wallet_transaction_id=transaction.id,
        external_reference="new_ref_123",
        provider_status="approved",
    )

    wallet.refresh_from_db()
    transaction.refresh_from_db()

    assert completed.id == transaction.id
    assert transaction.status == "COMPLETED"
    assert transaction.provider_status == "approved"
    assert transaction.external_reference == "new_ref_123"
    assert transaction.failure_reason is None
    assert transaction.completed_at is not None
    assert wallet.balance == Decimal("150.00")

    reference = f"wallet_transaction_{transaction.id}"
    entries = LedgerEntry.objects.filter(reference=reference).order_by("id")

    assert entries.count() == 2
    assert sum(entry.debit for entry in entries) == Decimal("150.00")
    assert sum(entry.credit for entry in entries) == Decimal("150.00")

    wallet_updated_log = AuditLog.objects.get(
        action="WALLET_UPDATED",
        entity_type="wallet",
        entity_id=wallet.id,
    )
    assert wallet_updated_log.metadata["change"] == "+150.00"
    assert wallet_updated_log.metadata["new_balance"] == "150.00"
    assert wallet_updated_log.metadata["reason"] == "wallet_top_up_completed"
    assert wallet_updated_log.metadata["wallet_transaction_id"] == transaction.id

    completed_log = AuditLog.objects.get(
        action="WALLET_TOP_UP_COMPLETED",
        entity_type="wallet_transaction",
        entity_id=transaction.id,
    )
    assert completed_log.metadata["wallet_id"] == wallet.id
    assert completed_log.metadata["amount"] == "150.00"
    assert completed_log.metadata["rail"] == "MERCADO_PAGO"
    assert completed_log.metadata["status"] == "COMPLETED"
    assert completed_log.metadata["provider_status"] == "approved"
    assert completed_log.metadata["external_reference"] == "new_ref_123"
    assert completed_log.metadata["reference"] == reference


@pytest.mark.django_db
def test_complete_top_up_returns_same_transaction_when_already_completed(wallet):
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("80.00"),
        status="COMPLETED",
        rail="MERCADO_PAGO",
        external_reference="done_ref",
        provider_status="approved",
    )

    result = WalletFundingService.complete_top_up(
        wallet_transaction_id=transaction.id,
        external_reference="ignored_new_ref",
        provider_status="approved",
    )

    wallet.refresh_from_db()
    transaction.refresh_from_db()

    assert result.id == transaction.id
    assert transaction.status == "COMPLETED"
    assert transaction.external_reference == "done_ref"
    assert wallet.balance == Decimal("0.00")
    assert not LedgerEntry.objects.filter(reference=f"wallet_transaction_{transaction.id}").exists()
    assert not AuditLog.objects.filter(
        action="WALLET_TOP_UP_COMPLETED",
        entity_id=transaction.id,
    ).exists()


@pytest.mark.django_db
def test_complete_top_up_rejects_failed_transaction(wallet):
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("80.00"),
        status="FAILED",
        rail="MERCADO_PAGO",
        external_reference="failed_ref",
        provider_status="rejected",
        failure_reason="cc_rejected_other_reason",
    )

    with pytest.raises(
        InvalidWalletTransactionOperation,
        match="Failed top-up cannot be marked as completed",
    ):
        WalletFundingService.complete_top_up(
            wallet_transaction_id=transaction.id,
            external_reference="ignored",
            provider_status="approved",
        )


@pytest.mark.django_db
def test_complete_top_up_rejects_non_top_up_transaction(wallet):
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="WITHDRAWAL",
        amount=Decimal("30.00"),
        status="PENDING",
        rail="SANDBOX",
        external_reference="withdrawal_ref",
        provider_status="PENDING",
    )

    with pytest.raises(
        InvalidWalletTransactionOperation,
        match="Only top-up transactions can be completed through this flow",
    ):
        WalletFundingService.complete_top_up(
            wallet_transaction_id=transaction.id,
            external_reference="ignored",
            provider_status="approved",
        )


@pytest.mark.django_db
def test_fail_top_up_marks_pending_transaction_as_failed_and_logs_audit(wallet):
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("95.00"),
        status="PENDING",
        rail="MERCADO_PAGO",
        external_reference="old_fail_ref",
        provider_status="CHECKOUT_CREATED",
    )

    failed = WalletFundingService.fail_top_up(
        wallet_transaction_id=transaction.id,
        provider_status="rejected",
        failure_reason="cc_rejected_other_reason",
        external_reference="new_fail_ref",
    )

    wallet.refresh_from_db()
    transaction.refresh_from_db()

    assert failed.id == transaction.id
    assert transaction.status == "FAILED"
    assert transaction.provider_status == "rejected"
    assert transaction.failure_reason == "cc_rejected_other_reason"
    assert transaction.external_reference == "new_fail_ref"
    assert wallet.balance == Decimal("0.00")

    failed_log = AuditLog.objects.get(
        action="WALLET_TOP_UP_FAILED",
        entity_type="wallet_transaction",
        entity_id=transaction.id,
    )
    assert failed_log.metadata["wallet_id"] == wallet.id
    assert failed_log.metadata["amount"] == "95.00"
    assert failed_log.metadata["rail"] == "MERCADO_PAGO"
    assert failed_log.metadata["status"] == "FAILED"
    assert failed_log.metadata["provider_status"] == "rejected"
    assert failed_log.metadata["failure_reason"] == "cc_rejected_other_reason"
    assert failed_log.metadata["external_reference"] == "new_fail_ref"


@pytest.mark.django_db
def test_fail_top_up_returns_same_transaction_when_already_failed(wallet):
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("40.00"),
        status="FAILED",
        rail="MERCADO_PAGO",
        external_reference="already_failed_ref",
        provider_status="rejected",
        failure_reason="already_failed",
    )

    result = WalletFundingService.fail_top_up(
        wallet_transaction_id=transaction.id,
        provider_status="rejected",
        failure_reason="ignored_reason",
        external_reference="ignored_ref",
    )

    transaction.refresh_from_db()

    assert result.id == transaction.id
    assert transaction.status == "FAILED"
    assert transaction.provider_status == "rejected"
    assert transaction.failure_reason == "already_failed"
    assert transaction.external_reference == "already_failed_ref"

    assert AuditLog.objects.filter(
        action="WALLET_TOP_UP_FAILED",
        entity_id=transaction.id,
    ).count() == 0


@pytest.mark.django_db
def test_fail_top_up_rejects_completed_transaction(wallet):
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="TOP_UP",
        amount=Decimal("70.00"),
        status="COMPLETED",
        rail="MERCADO_PAGO",
        external_reference="completed_ref",
        provider_status="approved",
    )

    with pytest.raises(
        InvalidWalletTransactionOperation,
        match="Completed top-up cannot be marked as failed",
    ):
        WalletFundingService.fail_top_up(
            wallet_transaction_id=transaction.id,
            provider_status="rejected",
            failure_reason="late_failure",
        )


@pytest.mark.django_db
def test_fail_top_up_rejects_non_top_up_transaction(wallet):
    transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="WITHDRAWAL",
        amount=Decimal("20.00"),
        status="PENDING",
        rail="SANDBOX",
        external_reference="withdrawal_ref_2",
        provider_status="PENDING",
    )

    with pytest.raises(
        InvalidWalletTransactionOperation,
        match="Only top-up transactions can be failed through this flow",
    ):
        WalletFundingService.fail_top_up(
            wallet_transaction_id=transaction.id,
            provider_status="rejected",
            failure_reason="invalid_op",
        )


@pytest.mark.django_db
def test_top_up_runs_full_sandbox_flow(wallet_user, wallet):
    transaction = WalletFundingService.top_up(
        user=wallet_user,
        amount=Decimal("110.00"),
        rail="SANDBOX",
        external_reference="sandbox_ref_1",
    )

    wallet.refresh_from_db()
    transaction.refresh_from_db()

    assert transaction.transaction_type == "TOP_UP"
    assert transaction.status == "COMPLETED"
    assert transaction.provider_status == "COMPLETED"
    assert transaction.external_reference == "sandbox_ref_1"
    assert wallet.balance == Decimal("110.00")

    reference = f"wallet_transaction_{transaction.id}"
    assert LedgerEntry.objects.filter(reference=reference).count() == 2


@pytest.mark.django_db
def test_withdraw_rejects_invalid_amount(wallet_user):
    with pytest.raises(InvalidWalletTransactionAmount):
        WalletFundingService.withdraw(
            user=wallet_user,
            amount=Decimal("0.00"),
        )


@pytest.mark.django_db
def test_withdraw_raises_when_wallet_does_not_exist():
    user = create_user_without_wallet(username="withdraw_without_wallet")

    with pytest.raises(WalletNotFound, match="Wallet not found for this user"):
        WalletFundingService.withdraw(
            user=user,
            amount=Decimal("20.00"),
        )


@pytest.mark.django_db
def test_withdraw_rejects_insufficient_balance(wallet_user, wallet):
    with pytest.raises(InsufficientBalance):
        WalletFundingService.withdraw(
            user=wallet_user,
            amount=Decimal("25.00"),
        )

    wallet.refresh_from_db()
    assert wallet.balance == Decimal("0.00")
    assert WalletTransaction.objects.count() == 0


@pytest.mark.django_db
def test_withdraw_completes_and_creates_ledger_and_audit(wallet_user, funded_wallet):
    transaction = WalletFundingService.withdraw(
        user=wallet_user,
        amount=Decimal("60.00"),
        rail="SANDBOX",
        external_reference="withdraw_ref_1",
    )

    funded_wallet.refresh_from_db()
    transaction.refresh_from_db()

    assert transaction.transaction_type == "WITHDRAWAL"
    assert transaction.status == "COMPLETED"
    assert transaction.provider_status == "COMPLETED"
    assert transaction.external_reference == "withdraw_ref_1"
    assert transaction.completed_at is not None
    assert funded_wallet.balance == Decimal("140.00")

    reference = f"wallet_transaction_{transaction.id}"
    entries = LedgerEntry.objects.filter(reference=reference).order_by("id")

    assert entries.count() == 2
    assert sum(entry.debit for entry in entries) == Decimal("60.00")
    assert sum(entry.credit for entry in entries) == Decimal("60.00")

    created_log = AuditLog.objects.get(
        action="WALLET_WITHDRAWAL_CREATED",
        entity_type="wallet_transaction",
        entity_id=transaction.id,
    )
    assert created_log.metadata["wallet_id"] == funded_wallet.id
    assert created_log.metadata["amount"] == "60.00"
    assert created_log.metadata["rail"] == "SANDBOX"
    assert created_log.metadata["status"] == "PENDING"
    assert created_log.metadata["provider_status"] == "COMPLETED"

    wallet_updated_log = AuditLog.objects.get(
        action="WALLET_UPDATED",
        entity_type="wallet",
        entity_id=funded_wallet.id,
    )
    assert wallet_updated_log.metadata["change"] == "-60.00"
    assert wallet_updated_log.metadata["new_balance"] == "140.00"
    assert wallet_updated_log.metadata["reason"] == "wallet_withdrawal"
    assert wallet_updated_log.metadata["wallet_transaction_id"] == transaction.id

    completed_log = AuditLog.objects.get(
        action="WALLET_WITHDRAWAL_COMPLETED",
        entity_type="wallet_transaction",
        entity_id=transaction.id,
    )
    assert completed_log.metadata["wallet_id"] == funded_wallet.id
    assert completed_log.metadata["amount"] == "60.00"
    assert completed_log.metadata["rail"] == "SANDBOX"
    assert completed_log.metadata["status"] == "COMPLETED"
    assert completed_log.metadata["provider_status"] == "COMPLETED"
    assert completed_log.metadata["reference"] == reference
    assert completed_log.metadata["external_reference"] == "withdraw_ref_1"


@pytest.mark.django_db
def test_withdraw_non_sandbox_starts_pending_provider_status_but_finishes_completed(wallet_user, funded_wallet):
    transaction = WalletFundingService.withdraw(
        user=wallet_user,
        amount=Decimal("35.00"),
        rail="BANK_TRANSFER",
        external_reference="bank_withdraw_ref",
    )

    funded_wallet.refresh_from_db()
    transaction.refresh_from_db()

    assert transaction.status == "COMPLETED"
    assert transaction.provider_status == "PENDING"
    assert transaction.external_reference == "bank_withdraw_ref"
    assert funded_wallet.balance == Decimal("165.00")
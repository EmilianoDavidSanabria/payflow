from django.db import transaction
from django.utils import timezone

from core.exceptions import (
    InsufficientBalance,
    InvalidWalletTransactionAmount,
    InvalidWalletTransactionOperation,
    WalletNotFound,
    WalletTransactionNotPending,
)
from services.audit_service import AuditService
from services.ledger_service import LedgerService
from wallets.models import Wallet, WalletTransaction


class WalletFundingService:

    @staticmethod
    @transaction.atomic
    def create_top_up_intent(
        user,
        amount,
        rail="SANDBOX",
        external_reference=None,
        provider_status="PENDING",
    ):
        if amount <= 0:
            raise InvalidWalletTransactionAmount()

        wallet = (
            Wallet.objects
            .select_for_update()
            .select_related("user")
            .filter(user=user)
            .first()
        )

        if wallet is None:
            raise WalletNotFound("Wallet not found for this user")

        wallet_transaction = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type="TOP_UP",
            amount=amount,
            status="PENDING",
            rail=rail,
            external_reference=external_reference,
            provider_status=provider_status,
        )

        AuditService.log_action(
            user=user,
            action="WALLET_TOP_UP_CREATED",
            entity_type="wallet_transaction",
            entity_id=wallet_transaction.id,
            metadata={
                "wallet_id": wallet.id,
                "amount": str(amount),
                "rail": rail,
                "status": wallet_transaction.status,
                "provider_status": wallet_transaction.provider_status,
                "external_reference": wallet_transaction.external_reference,
            },
        )

        return wallet_transaction

    @staticmethod
    @transaction.atomic
    def complete_top_up(wallet_transaction_id, external_reference, provider_status):
        wallet_transaction = (
            WalletTransaction.objects
            .select_for_update()
            .select_related("wallet", "wallet__user")
            .get(id=wallet_transaction_id)
        )

        if wallet_transaction.transaction_type != "TOP_UP":
            raise InvalidWalletTransactionOperation(
                "Only top-up transactions can be completed through this flow"
            )

        if wallet_transaction.status == "COMPLETED":
            return wallet_transaction

        if wallet_transaction.status == "FAILED":
            raise InvalidWalletTransactionOperation(
                "Failed top-up cannot be marked as completed"
            )

        if wallet_transaction.status != "PENDING":
            raise WalletTransactionNotPending()

        wallet = wallet_transaction.wallet

        wallet.balance += wallet_transaction.amount
        wallet.save(update_fields=["balance", "updated_at"])

        if external_reference:
            wallet_transaction.external_reference = external_reference

        wallet_transaction.status = "COMPLETED"
        wallet_transaction.provider_status = provider_status
        wallet_transaction.failure_reason = None
        wallet_transaction.completed_at = timezone.now()
        wallet_transaction.save(
            update_fields=[
                "status",
                "provider_status",
                "failure_reason",
                "external_reference",
                "completed_at",
                "updated_at",
            ]
        )

        AuditService.log_action(
            user=wallet.user,
            action="WALLET_UPDATED",
            entity_type="wallet",
            entity_id=wallet.id,
            metadata={
                "change": f"+{wallet_transaction.amount}",
                "new_balance": str(wallet.balance),
                "reason": "wallet_top_up_completed",
                "wallet_transaction_id": wallet_transaction.id,
            }
        )

        reference = f"wallet_transaction_{wallet_transaction.id}"

        LedgerService.top_up(
            user=wallet.user,
            amount=wallet_transaction.amount,
            reference=reference,
        )
        LedgerService.verify_integrity(reference)

        AuditService.log_action(
            user=wallet.user,
            action="WALLET_TOP_UP_COMPLETED",
            entity_type="wallet_transaction",
            entity_id=wallet_transaction.id,
            metadata={
                "wallet_id": wallet.id,
                "amount": str(wallet_transaction.amount),
                "rail": wallet_transaction.rail,
                "status": wallet_transaction.status,
                "provider_status": wallet_transaction.provider_status,
                "external_reference": wallet_transaction.external_reference,
                "reference": reference,
            }
        )

        return wallet_transaction

    @staticmethod
    @transaction.atomic
    def fail_top_up(
        wallet_transaction_id,
        provider_status="FAILED",
        failure_reason=None,
        external_reference=None,
    ):
        wallet_transaction = (
            WalletTransaction.objects
            .select_for_update()
            .select_related("wallet", "wallet__user")
            .get(id=wallet_transaction_id)
        )

        if wallet_transaction.transaction_type != "TOP_UP":
            raise InvalidWalletTransactionOperation(
                "Only top-up transactions can be failed through this flow"
            )

        if wallet_transaction.status == "FAILED":
            return wallet_transaction

        if wallet_transaction.status == "COMPLETED":
            raise InvalidWalletTransactionOperation(
                "Completed top-up cannot be marked as failed"
            )

        if wallet_transaction.status != "PENDING":
            raise WalletTransactionNotPending()

        if external_reference:
            wallet_transaction.external_reference = external_reference

        wallet_transaction.status = "FAILED"
        wallet_transaction.provider_status = provider_status
        wallet_transaction.failure_reason = failure_reason
        wallet_transaction.save(
            update_fields=[
                "status",
                "provider_status",
                "failure_reason",
                "external_reference",
                "updated_at",
            ]
        )

        AuditService.log_action(
            user=wallet_transaction.wallet.user,
            action="WALLET_TOP_UP_FAILED",
            entity_type="wallet_transaction",
            entity_id=wallet_transaction.id,
            metadata={
                "wallet_id": wallet_transaction.wallet.id,
                "amount": str(wallet_transaction.amount),
                "rail": wallet_transaction.rail,
                "status": wallet_transaction.status,
                "provider_status": wallet_transaction.provider_status,
                "failure_reason": wallet_transaction.failure_reason,
                "external_reference": wallet_transaction.external_reference,
            }
        )

        return wallet_transaction

    @staticmethod
    @transaction.atomic
    def top_up(user, amount, rail="SANDBOX", external_reference=None):
        wallet_transaction = WalletFundingService.create_top_up_intent(
            user=user,
            amount=amount,
            rail=rail,
            external_reference=external_reference,
            provider_status="PENDING",
        )

        return WalletFundingService.complete_top_up(
            wallet_transaction_id=wallet_transaction.id,
            external_reference=external_reference,
            provider_status="COMPLETED",
        )

    @staticmethod
    @transaction.atomic
    def withdraw(user, amount, rail="SANDBOX", external_reference=None):
        if amount <= 0:
            raise InvalidWalletTransactionAmount()

        wallet = (
            Wallet.objects
            .select_for_update()
            .filter(user=user)
            .first()
        )

        if wallet is None:
            raise WalletNotFound("Wallet not found for this user")

        if wallet.balance < amount:
            raise InsufficientBalance()

        wallet_transaction = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type="WITHDRAWAL",
            amount=amount,
            status="PENDING",
            rail=rail,
            external_reference=external_reference,
            provider_status="COMPLETED" if rail == "SANDBOX" else "PENDING",
        )

        AuditService.log_action(
            user=user,
            action="WALLET_WITHDRAWAL_CREATED",
            entity_type="wallet_transaction",
            entity_id=wallet_transaction.id,
            metadata={
                "wallet_id": wallet.id,
                "amount": str(amount),
                "rail": rail,
                "status": wallet_transaction.status,
                "provider_status": wallet_transaction.provider_status,
            }
        )

        wallet.balance -= amount
        wallet.save(update_fields=["balance", "updated_at"])

        AuditService.log_action(
            user=user,
            action="WALLET_UPDATED",
            entity_type="wallet",
            entity_id=wallet.id,
            metadata={
                "change": f"-{amount}",
                "new_balance": str(wallet.balance),
                "reason": "wallet_withdrawal",
                "wallet_transaction_id": wallet_transaction.id,
            }
        )

        reference = f"wallet_transaction_{wallet_transaction.id}"

        LedgerService.withdrawal(
            user=user,
            amount=amount,
            reference=reference,
        )
        LedgerService.verify_integrity(reference)

        wallet_transaction.status = "COMPLETED"
        wallet_transaction.completed_at = timezone.now()
        wallet_transaction.save(update_fields=["status", "completed_at", "updated_at"])

        AuditService.log_action(
            user=user,
            action="WALLET_WITHDRAWAL_COMPLETED",
            entity_type="wallet_transaction",
            entity_id=wallet_transaction.id,
            metadata={
                "wallet_id": wallet.id,
                "amount": str(amount),
                "rail": rail,
                "status": wallet_transaction.status,
                "provider_status": wallet_transaction.provider_status,
                "reference": reference,
                "external_reference": wallet_transaction.external_reference,
            }
        )

        return wallet_transaction
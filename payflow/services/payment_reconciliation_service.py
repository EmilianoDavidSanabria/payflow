from datetime import timedelta

from django.utils import timezone

from core.exceptions import InvalidWalletTransactionOperation
from wallets.models import WalletTransaction
from services.mercadopago_service import MercadoPagoService
from services.wallet_funding_service import WalletFundingService
from services.payment_event_service import PaymentEventService
from payments.events import PAYMENT_RECONCILED, PAYMENT_RECONCILIATION_DISCREPANCY


class PaymentReconciliationService:
    TERMINAL_FAILURE_STATUSES = {"rejected", "cancelled", "canceled"}
    STALE_PENDING_MINUTES = 30

    @staticmethod
    def _resolve_topup_transaction(tx, payment):
        provider_status = (payment.get("status") or "unknown").lower()
        failure_reason = payment.get("status_detail")
        provider_payment_id = payment.get("id")

        if provider_status == "approved":
            tx = WalletFundingService.complete_top_up(
                wallet_transaction_id=tx.id,
                external_reference=tx.external_reference,
                provider_status=provider_status,
            )

            PaymentEventService.log_event(
                action=PAYMENT_RECONCILED,
                entity_id=tx.id,
                metadata={
                    "provider_payment_id": str(provider_payment_id) if provider_payment_id else None,
                    "provider_status": provider_status,
                    "external_reference": tx.external_reference,
                    "result": "completed",
                },
            )
            return tx

        if provider_status in PaymentReconciliationService.TERMINAL_FAILURE_STATUSES:
            tx = WalletFundingService.fail_top_up(
                wallet_transaction_id=tx.id,
                provider_status=provider_status,
                failure_reason=failure_reason,
                external_reference=tx.external_reference,
            )

            PaymentEventService.log_event(
                action=PAYMENT_RECONCILED,
                entity_id=tx.id,
                metadata={
                    "provider_payment_id": str(provider_payment_id) if provider_payment_id else None,
                    "provider_status": provider_status,
                    "external_reference": tx.external_reference,
                    "failure_reason": failure_reason,
                    "result": "failed",
                },
            )
            return tx

        if tx.provider_status != provider_status:
            tx.provider_status = provider_status
            tx.save(update_fields=["provider_status", "updated_at"])

        return tx

    @staticmethod
    def refresh_topup_status(wallet_transaction):
        if wallet_transaction.transaction_type != "TOP_UP":
            raise InvalidWalletTransactionOperation(
                "Only top-up transactions can be refreshed through this flow"
            )

        if wallet_transaction.rail != "MERCADO_PAGO":
            raise InvalidWalletTransactionOperation(
                "Only Mercado Pago top-ups can be refreshed through this flow"
            )

        if wallet_transaction.status != "PENDING":
            return wallet_transaction

        if not wallet_transaction.external_reference:
            return wallet_transaction

        mp = MercadoPagoService()
        payment = mp.search_payment_by_external_reference(
            wallet_transaction.external_reference
        )

        if not payment:
            return wallet_transaction

        return PaymentReconciliationService._resolve_topup_transaction(
            wallet_transaction,
            payment,
        )

    @staticmethod
    def flag_stale_pending_topups(older_than_minutes=None):
        """
        Un top-up que sigue PENDING mucho después de haberse creado, y que
        ya intentamos reconciliar sin éxito, es una inconsistencia real
        entre PayFlow y el proveedor (no un simple estado transitorio).
        Esto lo deja registrado como evento auditable en vez de dejarlo
        pasar en silencio.
        """
        threshold_minutes = (
            older_than_minutes
            if older_than_minutes is not None
            else PaymentReconciliationService.STALE_PENDING_MINUTES
        )
        threshold = timezone.now() - timedelta(minutes=threshold_minutes)

        stale_transactions = WalletTransaction.objects.filter(
            transaction_type="TOP_UP",
            rail="MERCADO_PAGO",
            status="PENDING",
            created_at__lt=threshold,
        )

        flagged_ids = []

        for tx in stale_transactions:
            PaymentEventService.log_event(
                action=PAYMENT_RECONCILIATION_DISCREPANCY,
                entity_id=tx.id,
                metadata={
                    "rail": tx.rail,
                    "external_reference": tx.external_reference,
                    "amount": str(tx.amount),
                    "minutes_pending": int(
                        (timezone.now() - tx.created_at).total_seconds() // 60
                    ),
                    "reason": "topup_stuck_pending_past_threshold",
                },
            )
            flagged_ids.append(tx.id)

        return flagged_ids

    @staticmethod
    def reconcile_pending_topups():
        pending_transactions = WalletTransaction.objects.filter(
            transaction_type="TOP_UP",
            rail="MERCADO_PAGO",
            status="PENDING",
        )

        mp = MercadoPagoService()

        for tx in pending_transactions:
            try:
                if not tx.external_reference:
                    continue

                payment = mp.search_payment_by_external_reference(tx.external_reference)

                if not payment:
                    continue

                PaymentReconciliationService._resolve_topup_transaction(tx, payment)

            except Exception as exc:
                PaymentEventService.log_event(
                    action=PAYMENT_RECONCILED,
                    entity_id=tx.id,
                    metadata={
                        "external_reference": tx.external_reference,
                        "result": "error",
                        "error": str(exc),
                    },
                )

        PaymentReconciliationService.flag_stale_pending_topups()
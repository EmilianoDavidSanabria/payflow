from uuid import uuid4
from django.db import transaction, IntegrityError
from django.db import transaction
from django.utils import timezone
from services.risk_policy_service import RiskPolicyService
from payments.models import Payment, PaymentRequest
from wallets.models import Wallet

from services.ledger_service import LedgerService
from services.audit_service import AuditService
from payflow.events.payment_events import payment_completed_event
from core.exceptions import (
    InsufficientBalance,
    InvalidPaymentAmount,
    SelfPaymentNotAllowed,
    WalletNotFound,
    PaymentRequestActionNotAllowed,
    PaymentRequestAlreadyResolved,
)


class PaymentService:

    @staticmethod
    @transaction.atomic
    def create_payment(sender, receiver, amount, idempotency_key):
        existing_payment = Payment.objects.filter(
            idempotency_key=idempotency_key
        ).first()

        if existing_payment:
            return existing_payment

        if sender.id == receiver.id:
            raise SelfPaymentNotAllowed()

        if amount <= 0:
            raise InvalidPaymentAmount()

        RiskPolicyService.validate_payment(sender, amount)

        wallet_ids = sorted([sender.id, receiver.id])

        locked_wallets = Wallet.objects.select_for_update().filter(
            user_id__in=wallet_ids
        ).order_by("user_id")

        wallets = {
            wallet.user_id: wallet
            for wallet in locked_wallets
        }

        sender_wallet = wallets.get(sender.id)
        receiver_wallet = wallets.get(receiver.id)

        if sender_wallet is None:
            raise WalletNotFound("Sender wallet not found")

        if receiver_wallet is None:
            raise WalletNotFound("Receiver wallet not found")

        if sender_wallet.balance < amount:
            raise InsufficientBalance()

        try:
            with transaction.atomic():
                payment = Payment.objects.create(
                    sender=sender,
                    receiver=receiver,
                    amount=amount,
                    idempotency_key=idempotency_key,
                )
        except IntegrityError:
            return Payment.objects.get(idempotency_key=idempotency_key)

        reference = f"payment_{payment.id}"

        AuditService.log_action(
            user=sender,
            action="PAYMENT_CREATED",
            entity_type="payment",
            entity_id=payment.id,
            metadata={
                "amount": str(amount),
                "receiver": receiver.id,
                "receiver_username": receiver.username,
                "status": payment.status,
            }
        )

        sender_wallet.balance -= amount
        receiver_wallet.balance += amount

        sender_wallet.save(update_fields=["balance", "updated_at"])
        receiver_wallet.save(update_fields=["balance", "updated_at"])

        AuditService.log_action(
            user=sender,
            action="WALLET_UPDATED",
            entity_type="wallet",
            entity_id=sender_wallet.id,
            metadata={
                "change": f"-{amount}",
                "new_balance": str(sender_wallet.balance),
            }
        )

        AuditService.log_action(
            user=receiver,
            action="WALLET_UPDATED",
            entity_type="wallet",
            entity_id=receiver_wallet.id,
            metadata={
                "change": f"+{amount}",
                "new_balance": str(receiver_wallet.balance),
            }
        )

        LedgerService.transfer(
            sender,
            receiver,
            amount,
            reference=reference,
        )

        LedgerService.verify_integrity(reference)

        payment.status = "COMPLETED"
        payment.save(update_fields=["status"])

        AuditService.log_action(
            user=sender,
            action="PAYMENT_COMPLETED",
            entity_type="payment",
            entity_id=payment.id,
            metadata={
                "amount": str(amount),
                "receiver": receiver.id,
                "receiver_username": receiver.username,
                "reference": reference,
                "status": payment.status,
            }
        )

        transaction.on_commit(lambda: payment_completed_event(payment))

        return payment


    @staticmethod
    def create_payment_request(requester, requested_from, amount):
        if requester.id == requested_from.id:
            raise SelfPaymentNotAllowed()

        if amount <= 0:
            raise InvalidPaymentAmount()

        payment_request = PaymentRequest.objects.create(
            requester=requester,
            requested_from=requested_from,
            amount=amount,
        )

        AuditService.log_action(
            user=requester,
            action="PAYMENT_REQUEST_CREATED",
            entity_type="payment_request",
            entity_id=payment_request.id,
            metadata={
                "amount": str(amount),
                "requested_from": requested_from.id,
                "requested_from_username": requested_from.username,
                "status": payment_request.status,
            }
        )

        return payment_request

    @staticmethod
    @transaction.atomic
    def accept_payment_request(payment_request_id, actor):
        payment_request = (
            PaymentRequest.objects
            .select_for_update()
            .select_related("requester", "requested_from")
            .get(id=payment_request_id)
        )

        if payment_request.requested_from_id != actor.id:
            raise PaymentRequestActionNotAllowed()

        if payment_request.status != "PENDING":
            raise PaymentRequestAlreadyResolved()

        payment = PaymentService.create_payment(
            sender=payment_request.requested_from,
            receiver=payment_request.requester,
            amount=payment_request.amount,
            idempotency_key=f"payment-request-{payment_request.id}-{uuid4()}",
        )

        payment_request.status = "ACCEPTED"
        payment_request.accepted_payment = payment
        payment_request.resolved_at = timezone.now()
        payment_request.save()

        AuditService.log_action(
            user=actor,
            action="PAYMENT_REQUEST_ACCEPTED",
            entity_type="payment_request",
            entity_id=payment_request.id,
            metadata={
                "payment_id": payment.id,
                "amount": str(payment_request.amount),
                "requester_username": payment_request.requester.username,
                "status": payment_request.status,
            }
        )

        return payment_request

    @staticmethod
    @transaction.atomic
    def reject_payment_request(payment_request_id, actor):
        payment_request = (
            PaymentRequest.objects
            .select_for_update()
            .select_related("requester", "requested_from")
            .get(id=payment_request_id)
        )

        if payment_request.requested_from_id != actor.id:
            raise PaymentRequestActionNotAllowed()

        if payment_request.status != "PENDING":
            raise PaymentRequestAlreadyResolved()

        payment_request.status = "REJECTED"
        payment_request.resolved_at = timezone.now()
        payment_request.save()

        AuditService.log_action(
            user=actor,
            action="PAYMENT_REQUEST_REJECTED",
            entity_type="payment_request",
            entity_id=payment_request.id,
            metadata={
                "amount": str(payment_request.amount),
                "requester_username": payment_request.requester.username,
                "status": payment_request.status,
            }
        )

        return payment_request
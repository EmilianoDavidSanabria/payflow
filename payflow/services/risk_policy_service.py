from decimal import Decimal

from django.utils import timezone
from datetime import timedelta

from wallets.models import WalletTransaction
from payments.models import Payment
from core.exceptions import RiskCheckFailed


class RiskPolicyService:

    MAX_TOPUP_AMOUNT = Decimal("10000.00")
    MAX_WITHDRAW_AMOUNT = Decimal("5000.00")
    MAX_PAYMENT_AMOUNT = Decimal("10000.00")

    MAX_TOPUPS_PER_HOUR = 10
    MAX_WITHDRAWS_PER_HOUR = 5
    MAX_PAYMENTS_PER_HOUR = 20

    @staticmethod
    def validate_top_up(user, amount):

        if amount > RiskPolicyService.MAX_TOPUP_AMOUNT:
            raise RiskCheckFailed("Top-up amount exceeds allowed limit")

        one_hour_ago = timezone.now() - timedelta(hours=1)

        recent_topups = WalletTransaction.objects.filter(
            wallet__user=user,
            transaction_type="TOP_UP",
            created_at__gte=one_hour_ago,
        ).count()

        if recent_topups >= RiskPolicyService.MAX_TOPUPS_PER_HOUR:
            raise RiskCheckFailed("Too many top-ups in a short period")

    @staticmethod
    def validate_withdraw(user, amount):

        if amount > RiskPolicyService.MAX_WITHDRAW_AMOUNT:
            raise RiskCheckFailed("Withdrawal amount exceeds allowed limit")

        one_hour_ago = timezone.now() - timedelta(hours=1)

        recent_withdraws = WalletTransaction.objects.filter(
            wallet__user=user,
            transaction_type="WITHDRAWAL",
            created_at__gte=one_hour_ago,
        ).count()

        if recent_withdraws >= RiskPolicyService.MAX_WITHDRAWS_PER_HOUR:
            raise RiskCheckFailed("Too many withdrawals in a short period")

    @staticmethod
    def validate_payment(sender, amount):
        """
        Reglas básicas antifraude para pagos P2P. Se corre ANTES de tomar
        los locks de las billeteras (es solo una consulta de conteo, no
        tiene sentido correrla con filas lockeadas).
        """

        if amount > RiskPolicyService.MAX_PAYMENT_AMOUNT:
            raise RiskCheckFailed("Payment amount exceeds allowed limit")

        one_hour_ago = timezone.now() - timedelta(hours=1)

        recent_payments = Payment.objects.filter(
            sender=sender,
            created_at__gte=one_hour_ago,
        ).count()

        if recent_payments >= RiskPolicyService.MAX_PAYMENTS_PER_HOUR:
            raise RiskCheckFailed("Too many payments sent in a short period")
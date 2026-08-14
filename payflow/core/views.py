from datetime import timedelta
from decimal import Decimal

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth import get_user_model
from django.db.models import Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone

from payments.models import Payment
from wallets.models import Wallet, WalletTransaction
from ledger.models import LedgerEntry
from audit.models import AuditLog
from payments.serializers import PaymentSerializer
from wallets.serializers import WalletSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
User = get_user_model()


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "message": "PayFlow API is healthy"
            },
            status=status.HTTP_200_OK
        )


class MetricsView(APIView):
    """
    Platform-wide financial and operational totals (total volume, user
    counts, failure rates, etc). This aggregates data across every user
    on the platform, so it's restricted to staff — a regular authenticated
    user has no business seeing other users' aggregate activity.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        completed_payments_qs = Payment.objects.filter(status="COMPLETED")
        failed_payments_qs = Payment.objects.filter(status="FAILED")
        pending_payments_qs = Payment.objects.filter(status="PENDING")

        completed_top_ups_qs = WalletTransaction.objects.filter(
            transaction_type="TOP_UP",
            status="COMPLETED",
        )
        completed_withdrawals_qs = WalletTransaction.objects.filter(
            transaction_type="WITHDRAWAL",
            status="COMPLETED",
        )

        total_volume_transferred = completed_payments_qs.aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )["total"]

        total_top_up_volume = completed_top_ups_qs.aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )["total"]

        total_withdrawal_volume = completed_withdrawals_qs.aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )["total"]

        last_24_hours = timezone.now() - timedelta(hours=24)

        data = {
            "total_users": User.objects.count(),
            "total_wallets": Wallet.objects.count(),
            "total_payments": Payment.objects.count(),
            "total_wallet_transactions": WalletTransaction.objects.count(),
            "total_ledger_entries": LedgerEntry.objects.count(),
            "total_audit_logs": AuditLog.objects.count(),
            "completed_payments": completed_payments_qs.count(),
            "failed_payments": failed_payments_qs.count(),
            "pending_payments": pending_payments_qs.count(),
            "completed_top_ups": completed_top_ups_qs.count(),
            "completed_withdrawals": completed_withdrawals_qs.count(),
            "total_volume_transferred": f"{total_volume_transferred:.2f}",
            "total_top_up_volume": f"{total_top_up_volume:.2f}",
            "total_withdrawal_volume": f"{total_withdrawal_volume:.2f}",
            "payments_last_24h": Payment.objects.filter(
                created_at__gte=last_24_hours
            ).count(),
            "wallet_transactions_last_24h": WalletTransaction.objects.filter(
                created_at__gte=last_24_hours
            ).count(),
        }
        return Response(data, status=status.HTTP_200_OK)


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = request.user.wallet
        last_30_days = timezone.now() - timedelta(days=30)

        recent_payments = (
            Payment.objects
            .filter(Q(sender=request.user) | Q(receiver=request.user))
            .order_by("-created_at")[:5]
        )

        sent_payments_last_30_days = Payment.objects.filter(
            sender=request.user,
            status="COMPLETED",
            created_at__gte=last_30_days,
        )

        received_payments_last_30_days = Payment.objects.filter(
            receiver=request.user,
            status="COMPLETED",
            created_at__gte=last_30_days,
        )

        sent_total = sent_payments_last_30_days.aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )["total"]

        received_total = received_payments_last_30_days.aggregate(
            total=Coalesce(
                Sum("amount"),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )["total"]

        wallet_data = WalletSerializer(wallet).data
        recent_activity_data = PaymentSerializer(
            recent_payments,
            many=True,
            context={"request": request},
        ).data

        return Response(
            {
                "wallet": wallet_data,
                "recent_summary": {
                    "period_days": 30,
                    "sent_total": f"{sent_total:.2f}",
                    "received_total": f"{received_total:.2f}",
                    "sent_count": sent_payments_last_30_days.count(),
                    "received_count": received_payments_last_30_days.count(),
                },
                "recent_activity": recent_activity_data,
            },
            status=status.HTTP_200_OK
        )
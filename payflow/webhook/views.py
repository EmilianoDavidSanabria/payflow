from django.conf import settings

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.api_errors import error_response
from core.exceptions import (
    InvalidWalletTransactionOperation,
    WalletTransactionNotPending,
)
from services.wallet_funding_service import WalletFundingService
from wallets.models import WalletTransaction
from wallets.serializers import WalletTransactionSerializer



class BaseWebhookView(APIView):
    permission_classes = [AllowAny]

    def validate_secret(self, request):
        provided_secret = request.headers.get("X-Webhook-Secret")

        if provided_secret != settings.PAYFLOW_WEBHOOK_SECRET:
            return error_response(
                "Invalid webhook secret",
                status.HTTP_403_FORBIDDEN,
            )

        return None


class WalletTopUpCompleteWebhookView(BaseWebhookView):
    def post(self, request, transaction_id):
        secret_error = self.validate_secret(request)
        if secret_error:
            return secret_error

        try:
            wallet_transaction = WalletFundingService.complete_top_up(
                wallet_transaction_id=transaction_id,
                external_reference=request.data.get("external_reference"),
                provider_status=request.data.get("provider_status", "COMPLETED"),
            )
        except WalletTransaction.DoesNotExist:
            return error_response("Wallet transaction not found", status.HTTP_404_NOT_FOUND)
        except WalletTransactionNotPending:
            return error_response(
                "Wallet transaction is no longer pending",
                status.HTTP_400_BAD_REQUEST,
            )
        except InvalidWalletTransactionOperation as exc:
            return error_response(str(exc.detail), status.HTTP_400_BAD_REQUEST)

        serializer = WalletTransactionSerializer(wallet_transaction)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WalletTopUpFailWebhookView(BaseWebhookView):
    def post(self, request, transaction_id):
        secret_error = self.validate_secret(request)
        if secret_error:
            return secret_error

        try:
            wallet_transaction = WalletFundingService.fail_top_up(
                wallet_transaction_id=transaction_id,
                provider_status=request.data.get("provider_status", "FAILED"),
                failure_reason=request.data.get("failure_reason"),
                external_reference=request.data.get("external_reference"),
            )
        except WalletTransaction.DoesNotExist:
            return error_response("Wallet transaction not found", status.HTTP_404_NOT_FOUND)
        except WalletTransactionNotPending:
            return error_response(
                "Wallet transaction is no longer pending",
                status.HTTP_400_BAD_REQUEST,
            )
        except InvalidWalletTransactionOperation as exc:
            return error_response(str(exc.detail), status.HTTP_400_BAD_REQUEST)

        serializer = WalletTransactionSerializer(wallet_transaction)
        return Response(serializer.data, status=status.HTTP_200_OK)
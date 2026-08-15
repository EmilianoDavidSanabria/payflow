from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from core.api_errors import error_response
from core.exceptions import InsufficientBalance, InvalidWalletTransactionOperation
from core.pagination import paginate_queryset
from services.idempotency_service import IdempotencyService, IdempotencyKeyInProgress
from services.wallet_funding_service import WalletFundingService
from services.risk_policy_service import RiskPolicyService
from services.payment_reconciliation_service import PaymentReconciliationService
from wallets.models import WalletTransaction
from wallets.serializers import (
    WalletTopUpCreateSerializer,
    WalletWithdrawalCreateSerializer,
    WalletTransactionSerializer,
    WalletTransactionDetailSerializer,
)


def _get_idempotency_key(request):
    return request.headers.get("Idempotency-Key")


def _get_existing_idempotent_response(request):
    idempotency_key = _get_idempotency_key(request)

    if not idempotency_key:
        return None

    return IdempotencyService.get_existing_response(
        user=request.user,
        key=idempotency_key,
        request_path=request.path,
        request_method=request.method,
    )


def _create_idempotency_record(request):
    """
    Devuelve (record, is_new):
      - (None, True) si la request no mandó Idempotency-Key: no hay nada
        que cachear, seguir como flujo normal.
      - (record, True) si esta request ganó la carrera por esa key: es
        dueña de ejecutar la operación y debe guardar el resultado.
      - (record, False) si otra request concurrente ya terminó con esa
        misma key: el caller debe devolver record.response_body /
        record.response_code tal cual, sin volver a ejecutar nada.

    Puede levantar IdempotencyKeyInProgress si otra request con la misma
    key está siendo procesada ahora mismo (o quedó a medias).
    """
    idempotency_key = _get_idempotency_key(request)

    if not idempotency_key:
        return None, True

    return IdempotencyService.create_record(
        user=request.user,
        key=idempotency_key,
        request_path=request.path,
        request_method=request.method,
    )


class WalletTopUpView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WalletTopUpCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            existing = _get_existing_idempotent_response(request)
        except ValueError as exc:
            return error_response(str(exc), status.HTTP_400_BAD_REQUEST)

        if existing:
            body, status_code = existing
            return Response(body, status=status_code)

        try:
            record, is_new = _create_idempotency_record(request)
        except ValueError as exc:
            return error_response(str(exc), status.HTTP_400_BAD_REQUEST)
        except IdempotencyKeyInProgress:
            return error_response(
                "A request with this Idempotency-Key is already being processed",
                status.HTTP_409_CONFLICT,
            )

        if record and not is_new:
            return Response(record.response_body, status=record.response_code)

        try:
            wallet_transaction = WalletFundingService.top_up(
                user=request.user,
                amount=serializer.validated_data["amount"],
                rail="SANDBOX",
            )
        except InvalidWalletTransactionOperation as exc:
            response_body = {"error": str(exc.detail)}
            if record:
                IdempotencyService.save_response(
                    record,
                    response_body,
                    status.HTTP_400_BAD_REQUEST,
                )
            return error_response(str(exc.detail), status.HTTP_400_BAD_REQUEST)

        response_body = WalletTransactionSerializer(wallet_transaction).data

        if record:
            IdempotencyService.save_response(
                record,
                response_body,
                status.HTTP_201_CREATED,
            )

        return Response(response_body, status=status.HTTP_201_CREATED)


class WalletWithdrawalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WalletWithdrawalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            existing = _get_existing_idempotent_response(request)
        except ValueError as exc:
            return error_response(str(exc), status.HTTP_400_BAD_REQUEST)

        if existing:
            body, status_code = existing
            return Response(body, status=status_code)

        try:
            record, is_new = _create_idempotency_record(request)
        except ValueError as exc:
            return error_response(str(exc), status.HTTP_400_BAD_REQUEST)
        except IdempotencyKeyInProgress:
            return error_response(
                "A request with this Idempotency-Key is already being processed",
                status.HTTP_409_CONFLICT,
            )

        if record and not is_new:
            return Response(record.response_body, status=record.response_code)

        try:
            RiskPolicyService.validate_withdraw(
                user=request.user,
                amount=serializer.validated_data["amount"],
            )

            wallet_transaction = WalletFundingService.withdraw(
                user=request.user,
                amount=serializer.validated_data["amount"],
                rail="SANDBOX",
            )
        except InvalidWalletTransactionOperation as exc:
            response_body = {"error": str(exc.detail)}
            if record:
                IdempotencyService.save_response(
                    record,
                    response_body,
                    status.HTTP_400_BAD_REQUEST,
                )
            return error_response(str(exc.detail), status.HTTP_400_BAD_REQUEST)
        except InsufficientBalance:
            response_body = {"error": "Insufficient balance"}
            if record:
                IdempotencyService.save_response(
                    record,
                    response_body,
                    status.HTTP_400_BAD_REQUEST,
                )
            return error_response(
                "Insufficient balance",
                status.HTTP_400_BAD_REQUEST,
            )

        response_body = WalletTransactionSerializer(wallet_transaction).data

        if record:
            IdempotencyService.save_response(
                record,
                response_body,
                status.HTTP_201_CREATED,
            )

        return Response(response_body, status=status.HTTP_201_CREATED)


class WalletTransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transaction_type = request.query_params.get("type", "all")
        transaction_status = request.query_params.get("status", "all")
        rail = request.query_params.get("rail", "all")
        provider_status = request.query_params.get("provider_status", "all")

        transactions = WalletTransaction.objects.filter(wallet__user=request.user)

        allowed_types = {"all", "TOP_UP", "WITHDRAWAL"}
        allowed_statuses = {"all", "PENDING", "COMPLETED", "FAILED"}
        allowed_rails = {"all", "SANDBOX", "BANK_TRANSFER", "CARD", "MERCADO_PAGO"}

        if transaction_type not in allowed_types:
            return error_response("Invalid transaction type", status.HTTP_400_BAD_REQUEST)

        if transaction_status not in allowed_statuses:
            return error_response("Invalid transaction status", status.HTTP_400_BAD_REQUEST)

        if rail not in allowed_rails:
            return error_response("Invalid rail", status.HTTP_400_BAD_REQUEST)

        if transaction_type != "all":
            transactions = transactions.filter(transaction_type=transaction_type)

        if transaction_status != "all":
            transactions = transactions.filter(status=transaction_status)

        if rail != "all":
            transactions = transactions.filter(rail=rail)

        if provider_status != "all":
            transactions = transactions.filter(provider_status=provider_status)

        transactions = transactions.order_by("-created_at")

        pagination, error_response_result = paginate_queryset(transactions, request)
        if error_response_result:
            return error_response_result

        serializer = WalletTransactionSerializer(
            pagination["results"],
            many=True,
            context={"request": request}
        )

        return Response({
            "count": pagination["count"],
            "page": pagination["page"],
            "page_size": pagination["page_size"],
            "total_pages": pagination["total_pages"],
            "type": transaction_type,
            "status": transaction_status,
            "rail": rail,
            "results": serializer.data,
        }, status=status.HTTP_200_OK)

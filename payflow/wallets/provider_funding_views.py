from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from services.idempotency_service import IdempotencyService
from services.risk_policy_service import RiskPolicyService
from services.wallet_funding_service import WalletFundingService
from services.mercadopago_service import MercadoPagoService
from wallets.serializers import (
    WalletTopUpIntentCreateSerializer,
    WalletTransactionSerializer,
)
from services.payment_event_service import PaymentEventService
from payments.events import (
    PAYMENT_INTENT_CREATED,
    PAYMENT_CHECKOUT_CREATED,
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
    idempotency_key = _get_idempotency_key(request)

    if not idempotency_key:
        return None

    return IdempotencyService.create_record(
        user=request.user,
        key=idempotency_key,
        request_path=request.path,
        request_method=request.method,
    )


class WalletTopUpIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WalletTopUpIntentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            existing = _get_existing_idempotent_response(request)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if existing:
            body, status_code = existing
            return Response(body, status=status_code)

        try:
            record = _create_idempotency_record(request)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        RiskPolicyService.validate_top_up(
            user=request.user,
            amount=serializer.validated_data["amount"],
        )

        wallet_transaction = WalletFundingService.create_top_up_intent(
            user=request.user,
            amount=serializer.validated_data["amount"],
            rail=serializer.validated_data["rail"],
            provider_status="PENDING",
        )

        wallet_transaction.external_reference = str(wallet_transaction.id)
        wallet_transaction.save(update_fields=["external_reference", "updated_at"])

        PaymentEventService.log_event(
            action=PAYMENT_INTENT_CREATED,
            entity_id=wallet_transaction.id,
            metadata={
                "user_id": request.user.id,
                "amount": str(wallet_transaction.amount),
                "rail": wallet_transaction.rail,
                "external_reference": wallet_transaction.external_reference,
            },
        )

        if wallet_transaction.rail == "MERCADO_PAGO":
            try:
                mp_service = MercadoPagoService()
                preference = mp_service.create_top_up_preference(wallet_transaction)

                checkout_url = preference.get("checkout_url")
                if not checkout_url:
                    raise ValueError("Mercado Pago preference did not return a checkout URL")

                wallet_transaction.checkout_url = checkout_url
                wallet_transaction.provider_status = "CHECKOUT_CREATED"
                wallet_transaction.save(
                    update_fields=["checkout_url", "provider_status", "updated_at"]
                )

                PaymentEventService.log_event(
                    action=PAYMENT_CHECKOUT_CREATED,
                    entity_id=wallet_transaction.id,
                    metadata={
                        "user_id": request.user.id,
                        "amount": str(wallet_transaction.amount),
                        "rail": wallet_transaction.rail,
                        "external_reference": wallet_transaction.external_reference,
                        "checkout_url": wallet_transaction.checkout_url,
                        "provider_reference": preference.get("provider_reference"),
                    },
                )

            except Exception as exc:
                print(f"MERCADO PAGO PREFERENCE ERROR: {repr(exc)}")
                WalletFundingService.fail_top_up(
                    wallet_transaction_id=wallet_transaction.id,
                    provider_status="PREFERENCE_CREATION_FAILED",
                    failure_reason=str(exc),
                    external_reference=wallet_transaction.external_reference,
                )
                response_body = {
                    "detail": f"Could not create Mercado Pago checkout: {str(exc)}"
                }
                if record:
                    IdempotencyService.save_response(
                        record,
                        response_body,
                        status.HTTP_502_BAD_GATEWAY,
                    )
                return Response(
                    response_body,
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        response_body = WalletTransactionSerializer(wallet_transaction).data

        if record:
            IdempotencyService.save_response(
                record,
                response_body,
                status.HTTP_201_CREATED,
            )

        return Response(response_body, status=status.HTTP_201_CREATED)
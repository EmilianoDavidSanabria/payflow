import json
import traceback

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from services.mercadopago_service import MercadoPagoService
from services.wallet_funding_service import WalletFundingService
from services.payment_event_service import PaymentEventService

from wallets.models import WalletTransaction
from wallets.serializers import WalletTransactionSerializer

from payments.events import (
    WEBHOOK_RECEIVED,
    PAYMENT_APPROVED,
    PAYMENT_FAILED,
)

from webhook.utils import (
    webhook_event_already_processed,
    mark_webhook_event_processed,
)


class MercadoPagoWebhookView(APIView):
    permission_classes = [AllowAny]

    TERMINAL_FAILURE_STATUSES = {"rejected", "cancelled", "canceled"}

    def _get_body(self, request):
        try:
            if isinstance(request.data, dict):
                return request.data
        except Exception as exc:
            print(
                f"[MP WEBHOOK] request.data parse failed: {repr(exc)}",
                flush=True,
            )

        raw_body = request.body.decode("utf-8", errors="ignore") if request.body else ""

        if not raw_body:
            return {}

        try:
            parsed = json.loads(raw_body)
            return parsed if isinstance(parsed, dict) else {}
        except Exception as exc:
            print(
                f"[MP WEBHOOK] raw JSON parse failed: {repr(exc)} | raw_body={raw_body}",
                flush=True,
            )
            return {}

    def _extract_payment_id(self, request, body):
        nested_data = body.get("data")
        if isinstance(nested_data, dict):
            nested_id = nested_data.get("id")
            if nested_id:
                return str(nested_id)

        query_data_id = request.query_params.get("data.id")
        if query_data_id:
            return str(query_data_id)

        query_id = request.query_params.get("id")
        if query_id:
            return str(query_id)

        return None

    def _extract_event_id(self, request, body, payment_id):
        body_id = body.get("id")
        if body_id:
            return f"mp_event:{body_id}"

        action = body.get("action") or request.query_params.get("action") or "unknown"
        topic = (
            body.get("type")
            or body.get("topic")
            or request.query_params.get("type")
            or request.query_params.get("topic")
            or "unknown"
        )
        date_created = body.get("date_created") or request.query_params.get("date_created") or ""

        return f"mp_event_fallback:{topic}:{action}:{payment_id}:{date_created}"

    def post(self, request):
        try:
            body = self._get_body(request)

            print(
                "[MP WEBHOOK] incoming request | "
                f"content_type={request.content_type} | "
                f"path={request.path} | "
                f"query_params={dict(request.query_params)} | "
                f"body={body}",
                flush=True,
            )

            payment_id = self._extract_payment_id(request, body)

            if not payment_id:
                print("[MP WEBHOOK] ignored: missing payment_id", flush=True)
                return Response({"status": "ignored"}, status=status.HTTP_200_OK)

            event_id = self._extract_event_id(request, body, payment_id)

            print(
                f"[MP WEBHOOK] extracted ids | payment_id={payment_id} | event_id={event_id}",
                flush=True,
            )

            if webhook_event_already_processed("mercadopago", event_id):
                print(
                    f"[MP WEBHOOK] already processed | event_id={event_id}",
                    flush=True,
                )
                return Response({"status": "already_processed"}, status=status.HTTP_200_OK)

            try:
                payment = MercadoPagoService().get_payment(payment_id)
            except Exception as exc:
                print(
                    f"[MP WEBHOOK] MercadoPagoService.get_payment failed | "
                    f"payment_id={payment_id} | error={repr(exc)}",
                    flush=True,
                )
                return Response(
                    {"detail": f"Could not fetch payment from Mercado Pago: {str(exc)}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            print(
                f"[MP WEBHOOK] payment fetched | payment_id={payment_id} | payment={payment}",
                flush=True,
            )

            if not payment:
                print(
                    f"[MP WEBHOOK] empty payment response | payment_id={payment_id}",
                    flush=True,
                )
                return Response(
                    {"detail": "Could not fetch payment from Mercado Pago"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            external_reference = payment.get("external_reference")
            provider_status = str(payment.get("status") or "unknown").lower()
            failure_reason = payment.get("status_detail")

            print(
                "[MP WEBHOOK] payment mapped | "
                f"external_reference={external_reference} | "
                f"provider_status={provider_status} | "
                f"failure_reason={failure_reason}",
                flush=True,
            )

            if not external_reference:
                print("[MP WEBHOOK] missing external_reference", flush=True)
                return Response(
                    {"detail": "Missing external reference"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                wallet_transaction = WalletTransaction.objects.get(
                    id=int(external_reference),
                    transaction_type="TOP_UP",
                    rail="MERCADO_PAGO",
                )
            except (ValueError, WalletTransaction.DoesNotExist):
                print(
                    f"[MP WEBHOOK] wallet transaction not found | "
                    f"external_reference={external_reference}",
                    flush=True,
                )
                return Response(
                    {"detail": "Wallet transaction not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            print(
                "[MP WEBHOOK] wallet transaction found | "
                f"id={wallet_transaction.id} | "
                f"status={wallet_transaction.status} | "
                f"provider_status={wallet_transaction.provider_status}",
                flush=True,
            )

            PaymentEventService.log_event(
                action=WEBHOOK_RECEIVED,
                entity_id=wallet_transaction.id,
                metadata={
                    "event_id": event_id,
                    "payment_id": str(payment_id),
                    "provider_status": provider_status,
                    "external_reference": external_reference,
                },
            )

            if wallet_transaction.status != "PENDING":
                print(
                    f"[MP WEBHOOK] transaction already terminal | "
                    f"id={wallet_transaction.id} | status={wallet_transaction.status}",
                    flush=True,
                )
                mark_webhook_event_processed("mercadopago", event_id)
                serializer = WalletTransactionSerializer(wallet_transaction)
                return Response(serializer.data, status=status.HTTP_200_OK)

            if provider_status == "approved":
                print(
                    f"[MP WEBHOOK] completing top up | tx_id={wallet_transaction.id}",
                    flush=True,
                )

                wallet_transaction = WalletFundingService.complete_top_up(
                    wallet_transaction_id=wallet_transaction.id,
                    external_reference=wallet_transaction.external_reference,
                    provider_status=provider_status,
                )

                PaymentEventService.log_event(
                    action=PAYMENT_APPROVED,
                    entity_id=wallet_transaction.id,
                    metadata={
                        "event_id": event_id,
                        "payment_id": str(payment_id),
                        "provider_status": provider_status,
                        "external_reference": external_reference,
                    },
                )

            elif provider_status in self.TERMINAL_FAILURE_STATUSES:
                print(
                    f"[MP WEBHOOK] failing top up | tx_id={wallet_transaction.id}",
                    flush=True,
                )

                wallet_transaction = WalletFundingService.fail_top_up(
                    wallet_transaction_id=wallet_transaction.id,
                    provider_status=provider_status,
                    failure_reason=failure_reason,
                    external_reference=wallet_transaction.external_reference,
                )

                PaymentEventService.log_event(
                    action=PAYMENT_FAILED,
                    entity_id=wallet_transaction.id,
                    metadata={
                        "event_id": event_id,
                        "payment_id": str(payment_id),
                        "provider_status": provider_status,
                        "reason": failure_reason,
                        "external_reference": external_reference,
                    },
                )

            else:
                print(
                    "[MP WEBHOOK] non-terminal status, updating provider_status | "
                    f"tx_id={wallet_transaction.id} | provider_status={provider_status}",
                    flush=True,
                )
                wallet_transaction.provider_status = provider_status
                wallet_transaction.save(update_fields=["provider_status", "updated_at"])

            mark_webhook_event_processed("mercadopago", event_id)

            print(
                f"[MP WEBHOOK] processed successfully | tx_id={wallet_transaction.id}",
                flush=True,
            )

            serializer = WalletTransactionSerializer(wallet_transaction)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as exc:
            print(
                f"[MP WEBHOOK] unhandled exception: {repr(exc)}",
                flush=True,
            )
            print(traceback.format_exc(), flush=True)
            return Response(
                {"detail": "Internal webhook processing error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
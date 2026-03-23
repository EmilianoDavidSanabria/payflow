from datetime import datetime

from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q, Count

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.api_errors import error_response
from payments.models import Payment
from payments.serializers import (
    PaymentCreateSerializer,
    PaymentSerializer,
    RecentRecipientSerializer,
    FrequentRecipientSerializer,
)
from services.payment_service import PaymentService
from services.idempotency_service import IdempotencyService
from core.exceptions import InsufficientBalance
from core.pagination import paginate_queryset

User = get_user_model()


class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        idempotency_key = request.headers.get("Idempotency-Key")

        if not idempotency_key:
            return Response(
                {"error": "Idempotency-Key header required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        request_path = request.path
        request_method = request.method

        try:
            existing = IdempotencyService.get_existing_response(
                request.user,
                idempotency_key,
                request_path,
                request_method,
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if existing:
            body, status_code = existing
            return Response(body, status=status_code)

        try:
            record = IdempotencyService.create_record(
                request.user,
                idempotency_key,
                request_path,
                request_method,
            )
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        receiver = serializer.validated_data["receiver_username"]

        try:
            payment = PaymentService.create_payment(
                sender=request.user,
                receiver=receiver,
                amount=serializer.validated_data["amount"],
                idempotency_key=idempotency_key
            )
        except InsufficientBalance:
            response_body = {"error": "Insufficient balance"}
            IdempotencyService.save_response(
                record,
                response_body,
                status.HTTP_400_BAD_REQUEST
            )
            return Response(
                response_body,
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print("CREATE PAYMENT ERROR:", repr(e))
            response_body = {"error": f"Payment could not be created: {str(e)}"}
            IdempotencyService.save_response(
                record,
                response_body,
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response(
                response_body,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        response_body = PaymentSerializer(payment).data

        IdempotencyService.save_response(
            record,
            response_body,
            status.HTTP_201_CREATED
        )

        return Response(
            response_body,
            status=status.HTTP_201_CREATED
        )


class PaymentHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payment_type = request.query_params.get("type", "all")
        payment_status = request.query_params.get("status", "all")
        username = request.query_params.get("username")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if payment_type == "sent":
            payments = Payment.objects.filter(sender=request.user)
        elif payment_type == "received":
            payments = Payment.objects.filter(receiver=request.user)
        elif payment_type == "all":
            payments = Payment.objects.filter(
                Q(sender=request.user) | Q(receiver=request.user)
            )
        else:
            return error_response(
                "type must be one of: all, sent, received",
                status.HTTP_400_BAD_REQUEST,
            )

        allowed_statuses = {"all", "COMPLETED", "PENDING", "FAILED"}

        if payment_status not in allowed_statuses:
            return error_response(
                "status must be one of: all, COMPLETED, PENDING, FAILED",
                status.HTTP_400_BAD_REQUEST,
            )

        if payment_status != "all":
            payments = payments.filter(status=payment_status)

        if username:
            payments = payments.filter(
                Q(sender__username=username) | Q(receiver__username=username)
            )

        if date_from:
            try:
                parsed_from = datetime.strptime(date_from, "%Y-%m-%d").date()
                payments = payments.filter(created_at__date__gte=parsed_from)
            except ValueError:
                return error_response(
                    "date_from must be in YYYY-MM-DD format",
                    status.HTTP_400_BAD_REQUEST,
                )

        if date_to:
            try:
                parsed_to = datetime.strptime(date_to, "%Y-%m-%d").date()
                payments = payments.filter(created_at__date__lte=parsed_to)
            except ValueError:
                return error_response(
                    "date_to must be in YYYY-MM-DD format",
                    status.HTTP_400_BAD_REQUEST,
                )

        payments = payments.order_by("-created_at")

        pagination, error_response_result = paginate_queryset(payments, request)

        if error_response_result:
            return error_response_result

        serializer = PaymentSerializer(
            pagination["results"],
            many=True,
            context={"request": request},
        )

        return Response(
            {
                "count": pagination["count"],
                "page": pagination["page"],
                "page_size": pagination["page_size"],
                "total_pages": pagination["total_pages"],
                "type": payment_type,
                "status": payment_status,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK
        )


class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, id=payment_id)

        if payment.sender != request.user and payment.receiver != request.user:
            return Response(
                {"error": "Not authorized"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PaymentSerializer(payment, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecentRecipientsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        recent_payments = (
            Payment.objects
            .filter(sender=request.user, status="COMPLETED")
            .select_related("receiver")
            .order_by("receiver", "-created_at")
            .distinct("receiver")
        )

        data = [
            {
                "username": payment.receiver.username,
                "last_paid_at": payment.created_at,
            }
            for payment in recent_payments
        ]

        data.sort(key=lambda item: item["last_paid_at"], reverse=True)

        serializer = RecentRecipientSerializer(data, many=True)
        return Response(serializer.data[:6], status=status.HTTP_200_OK)


class FrequentRecipientsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        frequent_recipients = (
            Payment.objects
            .filter(sender=request.user, status="COMPLETED")
            .values("receiver__username")
            .annotate(payments_count=Count("id"))
            .order_by("-payments_count", "receiver__username")[:6]
        )

        data = [
            {
                "username": item["receiver__username"],
                "payments_count": item["payments_count"],
            }
            for item in frequent_recipients
        ]

        serializer = FrequentRecipientSerializer(data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
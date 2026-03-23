from datetime import datetime

from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.api_errors import error_response
from core.exceptions import (
    InsufficientBalance,
    PaymentRequestActionNotAllowed,
    PaymentRequestAlreadyResolved,
)
from core.pagination import paginate_queryset
from payments.models import PaymentRequest
from payments.serializers import (
    PaymentRequestCreateSerializer,
    PaymentRequestSerializer,
)
from services.payment_service import PaymentService


class CreatePaymentRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentRequestCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        requested_from = serializer.validated_data["requested_from_username"]

        payment_request = PaymentService.create_payment_request(
            requester=request.user,
            requested_from=requested_from,
            amount=serializer.validated_data["amount"],
        )

        response_body = PaymentRequestSerializer(
            payment_request,
            context={"request": request},
        ).data

        return Response(response_body, status=status.HTTP_201_CREATED)


class PaymentRequestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        request_type = request.query_params.get("type", "all")
        request_status = request.query_params.get("status", "all")
        username = request.query_params.get("username")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        if request_type == "incoming":
            payment_requests = PaymentRequest.objects.filter(requested_from=request.user)
        elif request_type == "outgoing":
            payment_requests = PaymentRequest.objects.filter(requester=request.user)
        elif request_type == "all":
            payment_requests = PaymentRequest.objects.filter(
                Q(requester=request.user) | Q(requested_from=request.user)
            )
        else:
            return error_response(
                "type must be one of: all, incoming, outgoing",
                status.HTTP_400_BAD_REQUEST,
            )

        allowed_statuses = {"all", "PENDING", "ACCEPTED", "REJECTED"}

        if request_status not in allowed_statuses:
            return error_response(
                "status must be one of: all, PENDING, ACCEPTED, REJECTED",
                status.HTTP_400_BAD_REQUEST,
            )

        if request_status != "all":
            payment_requests = payment_requests.filter(status=request_status)

        if username:
            payment_requests = payment_requests.filter(
                Q(requester__username=username) | Q(requested_from__username=username)
            )

        if date_from:
            try:
                parsed_from = datetime.strptime(date_from, "%Y-%m-%d").date()
                payment_requests = payment_requests.filter(created_at__date__gte=parsed_from)
            except ValueError:
                return error_response(
                    "date_from must be in YYYY-MM-DD format",
                    status.HTTP_400_BAD_REQUEST,
                )

        if date_to:
            try:
                parsed_to = datetime.strptime(date_to, "%Y-%m-%d").date()
                payment_requests = payment_requests.filter(created_at__date__lte=parsed_to)
            except ValueError:
                return error_response(
                    "date_to must be in YYYY-MM-DD format",
                    status.HTTP_400_BAD_REQUEST,
                )

        payment_requests = payment_requests.select_related(
            "requester",
            "requested_from",
            "accepted_payment",
        ).order_by("-created_at")

        pagination, error_response_result = paginate_queryset(payment_requests, request)

        if error_response_result:
            return error_response_result

        serializer = PaymentRequestSerializer(
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
                "type": request_type,
                "status": request_status,
                "username": username or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class PaymentRequestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        payment_request = get_object_or_404(
            PaymentRequest.objects.select_related(
                "requester",
                "requested_from",
                "accepted_payment",
            ),
            id=request_id,
        )

        if (
            payment_request.requester_id != request.user.id
            and payment_request.requested_from_id != request.user.id
        ):
            return error_response(
                "Not authorized",
                status.HTTP_403_FORBIDDEN,
            )

        serializer = PaymentRequestSerializer(
            payment_request,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcceptPaymentRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        try:
            payment_request = PaymentService.accept_payment_request(
                payment_request_id=request_id,
                actor=request.user,
            )
        except PaymentRequest.DoesNotExist:
            return error_response("Payment request not found", status.HTTP_404_NOT_FOUND)
        except PaymentRequestActionNotAllowed:
            return error_response(
                "You are not allowed to act on this payment request",
                status.HTTP_403_FORBIDDEN,
            )
        except PaymentRequestAlreadyResolved:
            return error_response(
                "Payment request is no longer pending",
                status.HTTP_400_BAD_REQUEST,
            )
        except InsufficientBalance:
            return error_response(
                "Insufficient balance",
                status.HTTP_400_BAD_REQUEST,
            )

        serializer = PaymentRequestSerializer(
            payment_request,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class RejectPaymentRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        try:
            payment_request = PaymentService.reject_payment_request(
                payment_request_id=request_id,
                actor=request.user,
            )
        except PaymentRequest.DoesNotExist:
            return error_response("Payment request not found", status.HTTP_404_NOT_FOUND)
        except PaymentRequestActionNotAllowed:
            return error_response(
                "You are not allowed to act on this payment request",
                status.HTTP_403_FORBIDDEN,
            )
        except PaymentRequestAlreadyResolved:
            return error_response(
                "Payment request is no longer pending",
                status.HTTP_400_BAD_REQUEST,
            )

        serializer = PaymentRequestSerializer(
            payment_request,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
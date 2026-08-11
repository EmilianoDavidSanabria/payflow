from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from audit.models import AuditLog
from audit.serializers import AuditLogSerializer
from core.pagination import paginate_queryset
from core.api_errors import error_response


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        action = request.query_params.get("action", "all")
        entity_type = request.query_params.get("entity_type", "all")

        logs = AuditLog.objects.filter(user=request.user)

        allowed_actions = {"all"} | {choice[0] for choice in AuditLog.ACTION_CHOICES}

        if action not in allowed_actions:
            return error_response(
                "action must be one of: all, " + ", ".join(sorted(allowed_actions - {"all"})),
                status.HTTP_400_BAD_REQUEST,
            )

        if action != "all":
            logs = logs.filter(action=action)

        allowed_entity_types = {
            "all",
            "payment",
            "wallet",
            "payment_request",
            "wallet_transaction",
        }

        if entity_type not in allowed_entity_types:
            return error_response(
                "entity_type must be one of: all, payment, wallet, payment_request, wallet_transaction",
                status.HTTP_400_BAD_REQUEST,
            )

        if entity_type != "all":
            logs = logs.filter(entity_type=entity_type)

        logs = logs.order_by("-created_at")

        pagination, error_response_result = paginate_queryset(logs, request)

        if error_response_result:
            return error_response_result

        serializer = AuditLogSerializer(pagination["results"], many=True)

        return Response(
            {
                "count": pagination["count"],
                "page": pagination["page"],
                "page_size": pagination["page_size"],
                "total_pages": pagination["total_pages"],
                "action": action,
                "entity_type": entity_type,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK
        )
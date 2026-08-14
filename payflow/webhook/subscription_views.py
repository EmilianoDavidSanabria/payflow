from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from webhook.models import Webhook
from webhook.serializers import WebhookSerializer


class WebhookListCreateView(APIView):
    """
    List the authenticated user's webhook subscriptions, or create a new one.

    Webhooks are always scoped to request.user: a user can only ever see,
    create, update or delete their own subscriptions.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        webhooks = Webhook.objects.filter(user=request.user).order_by("-created_at")
        serializer = WebhookSerializer(webhooks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = WebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WebhookDetailView(APIView):
    """
    Retrieve, update or delete a single webhook subscription owned by the
    authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, request, webhook_id):
        return get_object_or_404(Webhook, id=webhook_id, user=request.user)

    def get(self, request, webhook_id):
        webhook = self.get_object(request, webhook_id)
        serializer = WebhookSerializer(webhook)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, webhook_id):
        webhook = self.get_object(request, webhook_id)
        serializer = WebhookSerializer(webhook, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, webhook_id):
        webhook = self.get_object(request, webhook_id)
        webhook.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
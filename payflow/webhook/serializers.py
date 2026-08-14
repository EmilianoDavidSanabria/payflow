from rest_framework import serializers

from webhook.models import Webhook


class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = ["id", "url", "event", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]
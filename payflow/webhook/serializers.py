from rest_framework import serializers

from webhook.models import Webhook
from webhook.validators import validate_webhook_url


class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = ["id", "url", "event", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_url(self, value):
        return validate_webhook_url(value)
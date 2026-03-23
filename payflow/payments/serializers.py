from rest_framework import serializers
from django.contrib.auth import get_user_model

from payments.models import Payment, PaymentRequest

User = get_user_model()


class PaymentCreateSerializer(serializers.Serializer):
    receiver_username = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_receiver_username(self, value):
        try:
            user = User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        return user

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")

        return value

    def validate(self, attrs):
        request = self.context.get("request")

        if request.user == attrs["receiver_username"]:
            raise serializers.ValidationError(
                {"receiver_username": "You cannot send money to yourself"}
            )

        return attrs


class PaymentRequestCreateSerializer(serializers.Serializer):
    requested_from_username = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_requested_from_username(self, value):
        try:
            user = User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        return user

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")

        return value

    def validate(self, attrs):
        request = self.context.get("request")

        if request.user == attrs["requested_from_username"]:
            raise serializers.ValidationError(
                {"requested_from_username": "You cannot request money from yourself"}
            )

        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)
    receiver_username = serializers.CharField(source="receiver.username", read_only=True)
    direction = serializers.SerializerMethodField()
    counterparty_username = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "sender",
            "sender_username",
            "receiver",
            "receiver_username",
            "amount",
            "status",
            "idempotency_key",
            "created_at",
            "direction",
            "counterparty_username",
        ]

    def get_direction(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        if obj.sender_id == request.user.id:
            return "sent"

        if obj.receiver_id == request.user.id:
            return "received"

        return None

    def get_counterparty_username(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        if obj.sender_id == request.user.id:
            return obj.receiver.username

        if obj.receiver_id == request.user.id:
            return obj.sender.username

        return None


class PaymentRequestSerializer(serializers.ModelSerializer):
    requester_username = serializers.CharField(source="requester.username", read_only=True)
    requested_from_username = serializers.CharField(source="requested_from.username", read_only=True)
    direction = serializers.SerializerMethodField()
    counterparty_username = serializers.SerializerMethodField()
    accepted_payment_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PaymentRequest
        fields = [
            "id",
            "requester",
            "requester_username",
            "requested_from",
            "requested_from_username",
            "amount",
            "status",
            "accepted_payment_id",
            "created_at",
            "updated_at",
            "resolved_at",
            "direction",
            "counterparty_username",
        ]

    def get_direction(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        if obj.requester_id == request.user.id:
            return "outgoing"

        if obj.requested_from_id == request.user.id:
            return "incoming"

        return None

    def get_counterparty_username(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None

        if obj.requester_id == request.user.id:
            return obj.requested_from.username

        if obj.requested_from_id == request.user.id:
            return obj.requester.username

        return None


class RecentRecipientSerializer(serializers.Serializer):
    username = serializers.CharField()
    last_paid_at = serializers.DateTimeField()


class FrequentRecipientSerializer(serializers.Serializer):
    username = serializers.CharField()
    payments_count = serializers.IntegerField()
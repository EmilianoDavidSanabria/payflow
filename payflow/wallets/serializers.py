from rest_framework import serializers

from .models import Wallet, WalletTransaction


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = "__all__"
        read_only_fields = ["balance"]


class BaseWalletTransactionAmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value


class WalletTopUpCreateSerializer(BaseWalletTransactionAmountSerializer):
    pass


class WalletWithdrawalCreateSerializer(BaseWalletTransactionAmountSerializer):
    pass


class WalletTopUpIntentCreateSerializer(BaseWalletTransactionAmountSerializer):
    rail = serializers.ChoiceField(
        choices=[
            ("MERCADO_PAGO", "Mercado Pago"),
            ("CARD", "Card"),
            ("BANK_TRANSFER", "Bank Transfer"),
        ],
        default="MERCADO_PAGO",
    )


class WalletTransactionSerializer(serializers.ModelSerializer):
    wallet_id = serializers.IntegerField(source="wallet.id", read_only=True)

    class Meta:
        model = WalletTransaction
        fields = [
            "id",
            "wallet_id",
            "transaction_type",
            "amount",
            "status",
            "rail",
            "external_reference",
            "provider_status",
            "checkout_url",
            "failure_reason",
            "created_at",
            "updated_at",
            "completed_at",
        ]


class WalletTransactionDetailSerializer(serializers.ModelSerializer):
    wallet_id = serializers.IntegerField(source="wallet.id", read_only=True)
    can_resume_checkout = serializers.SerializerMethodField()

    class Meta:
        model = WalletTransaction
        fields = [
            "id",
            "wallet_id",
            "transaction_type",
            "amount",
            "status",
            "rail",
            "external_reference",
            "provider_status",
            "checkout_url",
            "can_resume_checkout",
            "failure_reason",
            "created_at",
            "updated_at",
            "completed_at",
        ]

    def get_can_resume_checkout(self, obj):
        return obj.status == "PENDING" and bool(obj.checkout_url)
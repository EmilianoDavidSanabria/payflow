from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Wallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="wallet"
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    currency = models.CharField(
        max_length=15,
        default="ARS"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance__gte=0),
                name="wallet_balance_non_negative",
            ),
        ]

    def __str__(self):
        return f"Wallet {self.user_id}"


class WalletTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ("TOP_UP", "Top Up"),
        ("WITHDRAWAL", "Withdrawal"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    RAIL_CHOICES = [
        ("SANDBOX", "Sandbox"),
        ("BANK_TRANSFER", "Bank Transfer"),
        ("CARD", "Card"),
        ("MERCADO_PAGO", "Mercado Pago"),
    ]

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    rail = models.CharField(
        max_length=30,
        choices=RAIL_CHOICES,
        default="SANDBOX",
    )

    external_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    provider_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text=(
            "ID del pago en el proveedor externo (ej: payment id de "
            "Mercado Pago) que efectivamente acreditó/completó esta "
            "transacción. Único cuando está presente: el mismo pago del "
            "proveedor no puede acreditar dos WalletTransaction distintas."
        ),
    )

    provider_status = models.CharField(
        max_length=50,
        default="NOT_APPLICABLE",
    )

    checkout_url = models.URLField(
        null=True,
        blank=True,
    )

    failure_reason = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"WalletTransaction {self.id} "
            f"{self.transaction_type} {self.amount} {self.status}"
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider_payment_id"],
                name="wallet_transaction_unique_provider_payment_id",
                condition=models.Q(provider_payment_id__isnull=False),
            ),
        ]


class WalletWithdrawal(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    RAIL_CHOICES = [
        ("BANK_TRANSFER", "Bank Transfer"),
        ("MERCADO_PAGO", "Mercado Pago"),
    ]

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="withdrawals",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    rail = models.CharField(
        max_length=30,
        choices=RAIL_CHOICES,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    destination_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    provider_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    failure_reason = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
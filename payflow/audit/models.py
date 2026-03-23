from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("PAYMENT_CREATED", "Payment Created"),
        ("PAYMENT_COMPLETED", "Payment Completed"),
        ("WALLET_UPDATED", "Wallet Updated"),
        ("PAYMENT_REQUEST_CREATED", "Payment Request Created"),
        ("PAYMENT_REQUEST_ACCEPTED", "Payment Request Accepted"),
        ("PAYMENT_REQUEST_REJECTED", "Payment Request Rejected"),
        ("WALLET_TOP_UP_CREATED", "Wallet Top Up Created"),
        ("WALLET_TOP_UP_COMPLETED", "Wallet Top Up Completed"),
        ("WALLET_TOP_UP_FAILED", "Wallet Top Up Failed"),
        ("WALLET_WITHDRAWAL_CREATED", "Wallet Withdrawal Created"),
        ("WALLET_WITHDRAWAL_COMPLETED", "Wallet Withdrawal Completed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES
    )

    entity_type = models.CharField(
        max_length=50
    )

    entity_id = models.IntegerField(
        null=True,
        blank=True
    )

    metadata = models.JSONField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.action} - {self.created_at}"
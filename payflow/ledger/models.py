from django.db import models
from django.conf import settings


class LedgerEntry(models.Model):

    ACCOUNT_TYPES = [
        ("USER", "User Wallet"),
        ("MERCHANT", "Merchant Wallet"),
        ("SYSTEM", "System"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES
    )

    debit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    reference = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.account_type} D:{self.debit} C:{self.credit}"
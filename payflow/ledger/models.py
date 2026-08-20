from django.conf import settings
from django.db import models
from django.db.models import Q


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
        blank=True,
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES,
    )

    debit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    reference = models.CharField(
        max_length=255,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="ledger_entry_non_negative_amounts",
                check=(
                    Q(debit__gte=0)
                    & Q(credit__gte=0)
                ),
            ),

            models.CheckConstraint(
                name="ledger_entry_exactly_one_side",
                check=(
                    Q(debit__gt=0, credit=0)
                    | Q(credit__gt=0, debit=0)
                ),
            ),

            models.UniqueConstraint(
                fields=["reference"],
                condition=Q(debit__gt=0),
                name="unique_debit_per_reference",
            ),

            models.UniqueConstraint(
                fields=["reference"],
                condition=Q(credit__gt=0),
                name="unique_credit_per_reference",
            ),
        ]

    def __str__(self):
        return (
            f"{self.reference} | "
            f"{self.account_type} "
            f"D:{self.debit} C:{self.credit}"
        )
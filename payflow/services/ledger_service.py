from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from ledger.models import LedgerEntry


class LedgerService:

    @staticmethod
    @transaction.atomic
    def _create_balanced_entries(
        debit_user,
        debit_account_type,
        credit_user,
        credit_account_type,
        amount,
        reference,
    ):
        """
        Creates the complete double-entry ledger record atomically.

        The database enforces:
        - debit and credit cannot be negative
        - exactly one side must be positive per entry
        - only one debit entry per reference
        - only one credit entry per reference
        """

        if amount <= Decimal("0.00"):
            raise ValueError("Ledger amount must be greater than zero")

        if not reference:
            raise ValueError("Ledger reference is required")

        entries = [
            LedgerEntry(
                user=debit_user,
                account_type=debit_account_type,
                debit=amount,
                credit=Decimal("0.00"),
                reference=reference,
            ),
            LedgerEntry(
                user=credit_user,
                account_type=credit_account_type,
                debit=Decimal("0.00"),
                credit=amount,
                reference=reference,
            ),
        ]

        LedgerEntry.objects.bulk_create(entries)

        return entries

    @staticmethod
    def transfer(sender, receiver, amount, reference):
        return LedgerService._create_balanced_entries(
            debit_user=sender,
            debit_account_type="USER",
            credit_user=receiver,
            credit_account_type="USER",
            amount=amount,
            reference=reference,
        )

    @staticmethod
    def top_up(user, amount, reference):
        return LedgerService._create_balanced_entries(
            debit_user=None,
            debit_account_type="SYSTEM",
            credit_user=user,
            credit_account_type="USER",
            amount=amount,
            reference=reference,
        )

    @staticmethod
    def withdrawal(user, amount, reference):
        return LedgerService._create_balanced_entries(
            debit_user=user,
            debit_account_type="USER",
            credit_user=None,
            credit_account_type="SYSTEM",
            amount=amount,
            reference=reference,
        )

    @staticmethod
    def verify_integrity(reference):
        totals = LedgerEntry.objects.filter(
            reference=reference
        ).aggregate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        )

        total_debit = totals["total_debit"] or Decimal("0.00")
        total_credit = totals["total_credit"] or Decimal("0.00")

        if total_debit != total_credit:
            raise ValueError(
                f"Ledger imbalance detected for reference {reference}"
            )

        return True
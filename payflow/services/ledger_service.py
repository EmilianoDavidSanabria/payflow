from decimal import Decimal

from django.db import transaction

from ledger.models import LedgerEntry


class LedgerService:
    @staticmethod
    @transaction.atomic
    def transfer(sender, receiver, amount, reference="payment"):
        LedgerEntry.objects.create(
            user=sender,
            account_type="USER",
            debit=amount,
            credit=0,
            reference=reference
        )

        LedgerEntry.objects.create(
            user=receiver,
            account_type="USER",
            debit=0,
            credit=amount,
            reference=reference
        )

    @staticmethod
    @transaction.atomic
    def top_up(user, amount, reference="wallet_top_up"):
        LedgerEntry.objects.create(
            user=None,
            account_type="SYSTEM",
            debit=amount,
            credit=0,
            reference=reference
        )

        LedgerEntry.objects.create(
            user=user,
            account_type="USER",
            debit=0,
            credit=amount,
            reference=reference
        )

    @staticmethod
    @transaction.atomic
    def withdrawal(user, amount, reference="wallet_withdrawal"):
        LedgerEntry.objects.create(
            user=user,
            account_type="USER",
            debit=amount,
            credit=0,
            reference=reference
        )

        LedgerEntry.objects.create(
            user=None,
            account_type="SYSTEM",
            debit=0,
            credit=amount,
            reference=reference
        )

    @staticmethod
    def verify_integrity(reference):
        entries = LedgerEntry.objects.filter(reference=reference)

        total_debit = sum((entry.debit for entry in entries), Decimal("0.00"))
        total_credit = sum((entry.credit for entry in entries), Decimal("0.00"))

        if total_debit != total_credit:
            raise ValueError("Ledger imbalance detected")
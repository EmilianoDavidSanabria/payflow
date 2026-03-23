from django.core.management.base import BaseCommand

from services.payment_reconciliation_service import PaymentReconciliationService


class Command(BaseCommand):

    help = "Reconcile pending payment transactions with providers"

    def handle(self, *args, **options):

        PaymentReconciliationService.reconcile_pending_topups()

        self.stdout.write(
            self.style.SUCCESS("Payment reconciliation finished successfully")
        )
from django.core.management.base import BaseCommand

from services.payment_reconciliation_service import PaymentReconciliationService


class Command(BaseCommand):
    help = "Reconcile pending Mercado Pago wallet top-ups"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING("Starting reconciliation of pending Mercado Pago top-ups...")
        )

        PaymentReconciliationService.reconcile_pending_topups()

        self.stdout.write(
            self.style.SUCCESS("Reconciliation finished successfully.")
        )
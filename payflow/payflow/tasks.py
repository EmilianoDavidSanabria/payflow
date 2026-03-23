from celery import shared_task

from services.payment_reconciliation_service import PaymentReconciliationService


@shared_task
def reconcile_pending_payments():

    PaymentReconciliationService.reconcile_pending_topups()
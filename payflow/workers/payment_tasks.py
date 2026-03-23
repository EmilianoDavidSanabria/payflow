from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_payment_notification(self, payment_id):

    print(f"Sending notification for payment {payment_id}")
from celery import shared_task
from services.webhook_services import WebhookService


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True)
def dispatch_webhook(self, event, payload, user_ids=None):

    WebhookService.send_event(event, payload, user_ids=user_ids)
from django.db import IntegrityError

from webhook.models import ProcessedWebhookEvent


def webhook_event_already_processed(provider, event_id):
    return ProcessedWebhookEvent.objects.filter(
        provider=provider,
        event_id=event_id,
    ).exists()


def mark_webhook_event_processed(provider, event_id):
    try:
        _, created = ProcessedWebhookEvent.objects.get_or_create(
            provider=provider,
            event_id=event_id,
        )
        return created
    except IntegrityError:
        return False
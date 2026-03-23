import requests
from webhook.models import Webhook


class WebhookService:

    @staticmethod
    def send_event(event, payload):

        webhooks = Webhook.objects.filter(
            event=event,
            is_active=True
        )

        for webhook in webhooks:

            try:
                requests.post(
                    webhook.url,
                    json=payload,
                    timeout=5
                )

            except Exception:
                pass
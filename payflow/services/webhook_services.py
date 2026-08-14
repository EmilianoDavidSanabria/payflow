import requests
from webhook.models import Webhook


class WebhookService:

    @staticmethod
    def send_event(event, payload, user_ids=None):
        """
        Dispatches `event` with `payload` to active webhooks subscribed to it.

        `user_ids`, when provided, restricts delivery to webhooks owned by
        those users only (e.g. the sender/receiver of a payment). This
        prevents any user who subscribes to an event from receiving data
        about other users' activity. If `user_ids` is None, the event is
        broadcast to every active subscriber for that event (only safe for
        platform-wide events with no per-user data).
        """

        webhooks = Webhook.objects.filter(
            event=event,
            is_active=True
        )

        if user_ids is not None:
            webhooks = webhooks.filter(user_id__in=user_ids)

        for webhook in webhooks:

            try:
                requests.post(
                    webhook.url,
                    json=payload,
                    timeout=5,
                    # The URL was validated against internal/private targets
                    # at creation time, but a remote server could still
                    # redirect us to an internal address at send time.
                    # Refusing to follow redirects closes that gap.
                    allow_redirects=False,
                )

            except Exception:
                pass
from django.db import models
from django.conf import settings


class Webhook(models.Model):

    EVENT_CHOICES = [
        ("payment_completed", "Payment Completed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    url = models.URLField()

    event = models.CharField(
        max_length=50,
        choices=EVENT_CHOICES
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event} -> {self.url}"
    
class ProcessedWebhookEvent(models.Model):

    provider = models.CharField(max_length=50)

    event_id = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("provider", "event_id")

    def __str__(self):
        return f"{self.provider}:{self.event_id}"
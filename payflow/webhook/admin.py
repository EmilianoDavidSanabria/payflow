from django.contrib import admin

from webhook.models import Webhook, ProcessedWebhookEvent


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "event", "url", "is_active", "created_at")
    list_filter = ("event", "is_active")
    search_fields = ("url", "user__username", "user__email")
    autocomplete_fields = ("user",)


@admin.register(ProcessedWebhookEvent)
class ProcessedWebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "event_id", "created_at")
    list_filter = ("provider",)
    search_fields = ("event_id",)
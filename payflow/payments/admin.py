from django.contrib import admin

from payments.models import Payment, PaymentRequest


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "receiver", "amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = (
        "id",
        "idempotency_key",
        "sender__username",
        "sender__email",
        "receiver__username",
        "receiver__email",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = ("sender", "receiver")


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "requester", "requested_from", "amount", "status", "accepted_payment")
    list_filter = ("status",)
    search_fields = (
        "id",
        "requester__username",
        "requester__email",
        "requested_from__username",
        "requested_from__email",
    )
    autocomplete_fields = ("requester", "requested_from", "accepted_payment")
from django.contrib import admin

from wallets.models import Wallet, WalletTransaction, WalletWithdrawal


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "balance", "currency", "updated_at")
    search_fields = ("user__username", "user__email")
    autocomplete_fields = ("user",)


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "wallet",
        "transaction_type",
        "amount",
        "status",
        "rail",
        "provider_status",
        "created_at",
    )
    list_filter = ("transaction_type", "status", "rail")
    search_fields = ("wallet__user__username", "wallet__user__email", "external_reference")
    date_hierarchy = "created_at"
    autocomplete_fields = ("wallet",)


@admin.register(WalletWithdrawal)
class WalletWithdrawalAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet", "amount", "rail", "status", "created_at")
    list_filter = ("rail", "status")
    search_fields = ("wallet__user__username", "wallet__user__email", "destination_reference")
    date_hierarchy = "created_at"
    autocomplete_fields = ("wallet",)
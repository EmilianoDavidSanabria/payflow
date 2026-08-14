from django.contrib import admin

from ledger.models import LedgerEntry


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "account_type", "user", "debit", "credit", "reference", "created_at")
    list_filter = ("account_type",)
    search_fields = ("user__username", "user__email", "reference")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in LedgerEntry._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
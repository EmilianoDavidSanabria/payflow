from django.contrib import admin

from idempotency.models import IdempotencyKey


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ("id", "key", "request_method", "request_path", "response_code", "created_at")
    list_filter = ("request_method", "response_code")
    search_fields = ("key", "request_path")
    readonly_fields = [f.name for f in IdempotencyKey._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
from django.contrib import admin

from .models import PointBatch, PointTransaction


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ("customer", "kind", "points", "purchase_amount", "staff", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("customer__display_name", "customer__line_user_id")


@admin.register(PointBatch)
class PointBatchAdmin(admin.ModelAdmin):
    list_display = ("customer", "earned_points", "remaining_points", "earned_at", "expires_at", "is_expired")
    list_filter = ("is_expired", "expires_at")
    search_fields = ("customer__display_name",)

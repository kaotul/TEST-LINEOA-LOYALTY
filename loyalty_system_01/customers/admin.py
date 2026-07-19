from django.contrib import admin

from .models import Customer, StaffProfile


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "line_user_id", "qr_token", "current_point_balance", "is_active", "created_at")
    search_fields = ("display_name", "line_user_id", "qr_token", "phone_number")
    readonly_fields = ("qr_token", "created_at", "updated_at")


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "branch_name")

from django.contrib import admin
from .models import Store, Customer


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    search_fields = ("name", "code")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "line_user_id", "member_code", "phone_number", "is_active", "registered_at")
    search_fields = ("display_name", "line_user_id", "phone_number", "member_code")
    readonly_fields = ("line_user_id", "member_code", "registered_at", "last_login_at")

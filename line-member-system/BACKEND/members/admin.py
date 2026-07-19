from django.contrib import admin

from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("member_no", "first_name", "last_name", "phone_number", "email", "created_at", "is_active")
    search_fields = ("member_no", "first_name", "last_name", "phone_number", "email", "line_user_id")
    list_filter = ("is_active", "created_at")
    readonly_fields = ("line_user_id", "member_no", "created_at", "updated_at")

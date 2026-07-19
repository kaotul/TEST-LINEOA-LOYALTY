from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import StaffUser


@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "store", "is_active")
    list_filter = ("role", "store", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("ข้อมูลตำแหน่งงาน", {"fields": ("role", "store")}),
    )

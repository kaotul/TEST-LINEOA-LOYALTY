from django.contrib import admin
from .models import PointsSetting, PointTransaction


@admin.register(PointsSetting)
class PointsSettingAdmin(admin.ModelAdmin):
    list_display = ("baht_per_point", "point_expiry_days", "expiry_warning_days")

    def has_add_permission(self, request):
        # Singleton: อนุญาตให้เพิ่มได้แค่ครั้งเดียว
        return not PointsSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "customer", "tx_type", "points", "balance_after", "store", "staff", "expire_date", "created_at",
    )
    list_filter = ("tx_type", "store", "created_at")
    search_fields = ("customer__display_name", "customer__line_user_id", "customer__member_code")
    readonly_fields = [f.name for f in PointTransaction._meta.fields]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        # ห้ามสร้างรายการตรงจาก admin — ต้องผ่าน service เท่านั้น เพื่อรักษาความถูกต้องของยอดคงเหลือ
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if getattr(user, "is_manager_role", False) or user.is_superuser:
            return qs
        if getattr(user, "store_id", None):
            return qs.filter(store_id=user.store_id)
        return qs.none()

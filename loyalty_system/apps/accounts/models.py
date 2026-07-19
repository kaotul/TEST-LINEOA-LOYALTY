from django.contrib.auth.models import AbstractUser
from django.db import models


class StaffUser(AbstractUser):
    """
    ผู้ใช้งานฝั่งหน้าบ้าน (Dashboard/POS) — login ด้วย username/password (local)
    ไม่เกี่ยวข้องกับลูกค้าที่ login ผ่าน LINE LIFF
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "ผู้ดูแลระบบ"
        MANAGER = "manager", "ผู้จัดการ (ดูรายงานทุกสาขา)"
        STAFF = "staff", "พนักงานหน้าร้าน (ให้/แลกแต้ม)"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    store = models.ForeignKey(
        "customers.Store",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_members",
        help_text="สาขาที่พนักงานประจำอยู่ (ผู้ดูแลระบบ/ผู้จัดการ เว้นว่างได้ = เข้าถึงทุกสาขา)",
    )

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_manager_role(self):
        return self.role in (self.Role.ADMIN, self.Role.MANAGER)

    @property
    def can_manage_settings(self):
        return self.role == self.Role.ADMIN

    @property
    def can_award_points(self):
        return self.role in (self.Role.ADMIN, self.Role.MANAGER, self.Role.STAFF)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

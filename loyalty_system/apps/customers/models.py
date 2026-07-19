import uuid
from django.db import models


class Store(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    """
    ลูกค้าที่ลงทะเบียน/login ผ่าน LINE OA (LIFF)
    line_user_id คือ 'sub' ที่ได้จากการ verify LIFF id_token — ใช้เป็น identity หลัก
    """

    line_user_id = models.CharField(max_length=64, unique=True, db_index=True)
    display_name = models.CharField(max_length=150, blank=True)
    picture_url = models.URLField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    # member_code = รหัสสมาชิกที่เข้ารหัสลง QR สำหรับให้พนักงานสแกน
    member_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    is_active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-registered_at"]

    def __str__(self):
        return self.display_name or str(self.member_code)

    @property
    def qr_payload(self):
        """ข้อมูลที่เข้ารหัสอยู่ใน QR Code ของลูกค้า"""
        return f"LOYALTY:{self.member_code}"

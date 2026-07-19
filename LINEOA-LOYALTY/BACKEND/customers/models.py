import uuid

from django.db import models


class Customer(models.Model):
    """
    ลูกค้าหนึ่งคน ผูกกับ LINE userId (จาก LINE Login ผ่าน LIFF / Messaging API)
    qr_token คือรหัสประจำตัวที่ใช้ฝังใน QR Code ให้พนักงานสแกน
    (ใช้ UUID แทนการ encode line_user_id ตรง ๆ เพื่อไม่ให้เดา/ปลอมได้ง่าย)

    วงจรชีวิตสมาชิก (กติกาข้อ 1):
    1) ลูกค้าเพิ่มเพื่อน LINE OA -> webhook สร้าง record โครงร่าง (is_registered=False)
    2) ลูกค้าเปิดปุ่มบน Rich Menu -> LIFF ตรวจ id_token กับ LINE (LINE Login)
       ถ้ายังไม่ลงทะเบียน จะให้กรอกฟอร์มสมัครสมาชิก (ชื่อ, เบอร์โทร, ยอมรับเงื่อนไข)
    3) ยืนยันสำเร็จ -> is_registered=True, registered_at ถูกบันทึก -> ใช้งานระบบแต้ม/QR ได้เต็มรูปแบบ
    """
    qr_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    line_user_id = models.CharField(max_length=64, unique=True, db_index=True)
    display_name = models.CharField(max_length=150, blank=True)
    picture_url = models.URLField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    is_registered = models.BooleanField(default=False, help_text="ผ่านขั้นตอนลงทะเบียนสมาชิกครบถ้วนแล้วหรือยัง")
    registered_at = models.DateTimeField(null=True, blank=True)
    consent_accepted = models.BooleanField(default=False, help_text="ยอมรับเงื่อนไข/นโยบายความเป็นส่วนตัว")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.display_name or self.line_user_id} ({self.qr_token})"

    @property
    def current_point_balance(self) -> int:
        """แต้มคงเหลือจริง = แต้มที่ยัง active และยังไม่หมดอายุ"""
        from points.models import PointBatch

        agg = PointBatch.objects.filter(
            customer=self, is_expired=False
        ).aggregate(total=models.Sum("remaining_points"))
        return agg["total"] or 0


class StaffProfile(models.Model):
    """
    พนักงานหน้าร้านที่มีสิทธิ์ใช้ POS Dashboard สแกน QR และให้แต้ม
    ผูกกับ django.contrib.auth.User มาตรฐาน เพื่อใช้ระบบ auth/permission เดิมของ Django
    """
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, related_name="staff_profile")
    branch_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Staff: {self.user.get_username()} ({self.branch_name})"

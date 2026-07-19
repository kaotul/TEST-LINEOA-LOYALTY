from django.conf import settings
from django.db import models
from django.utils import timezone


class PointTransaction(models.Model):
    """
    ประวัติการรับ/แลกคะแนนทุกรายการ (ใช้แสดงในหน้า LIFF: ประวัติการรับ-แลกคะแนน)
    """
    class Kind(models.TextChoices):
        EARN = "EARN", "รับคะแนน"
        REDEEM = "REDEEM", "แลกคะแนน"
        EXPIRE = "EXPIRE", "คะแนนหมดอายุ"
        ADJUST = "ADJUST", "ปรับปรุงคะแนน (แอดมิน)"

    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="transactions")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    points = models.IntegerField(help_text="ค่าบวก = ได้รับ, ค่าลบ = แลก/หมดอายุ/หัก")
    purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    staff = models.ForeignKey("customers.StaffProfile", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer} {self.kind} {self.points} @ {self.created_at:%Y-%m-%d}"


class PointBatch(models.Model):
    """
    'ก้อนแต้ม' แต่ละครั้งที่ลูกค้าได้รับ พร้อมวันหมดอายุของก้อนนั้น ๆ
    ใช้หลัก FIFO: ตอนแลก/หักแต้ม จะตัดจากก้อนที่หมดอายุเร็วสุดก่อน
    ทำให้ระบบตอบได้ตรงว่า "คะแนนที่กำลังจะหมดอายุ" มีเท่าไหร่ ภายในกี่วัน
    """
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="point_batches")
    origin_transaction = models.OneToOneField(
        PointTransaction, on_delete=models.CASCADE, related_name="batch"
    )
    earned_points = models.PositiveIntegerField()
    remaining_points = models.PositiveIntegerField()
    earned_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    is_expired = models.BooleanField(default=False)

    class Meta:
        ordering = ["expires_at"]  # FIFO ตามวันหมดอายุที่ใกล้สุดก่อน
        indexes = [
            models.Index(fields=["customer", "is_expired", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.customer} +{self.earned_points} (เหลือ {self.remaining_points}) หมดอายุ {self.expires_at:%Y-%m-%d}"

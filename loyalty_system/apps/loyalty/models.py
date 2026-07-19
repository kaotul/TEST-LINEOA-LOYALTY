from django.conf import settings
from django.db import models
from django.utils import timezone


class PointsSetting(models.Model):
    """
    ตั้งค่ากลางของระบบสะสมแต้ม (Singleton — มีแถวเดียว)
    แก้ไขได้จาก Django admin โดย role=admin เท่านั้น
    """

    baht_per_point = models.DecimalField(
        max_digits=10, decimal_places=2, default=settings.DEFAULT_BAHT_PER_POINT,
        help_text="ทุกยอดซื้อกี่บาท ถึงจะได้ 1 คะแนน (เช่น 50 = ทุก 50 บาท ได้ 1 แต้ม)",
    )
    point_expiry_days = models.PositiveIntegerField(
        default=settings.DEFAULT_POINT_EXPIRY_DAYS,
        help_text="จำนวนวันก่อนแต้มจะหมดอายุ นับจากวันที่ได้รับ",
    )
    expiry_warning_days = models.PositiveIntegerField(
        default=settings.EXPIRY_WARNING_DAYS,
        help_text="แจ้งเตือนล่วงหน้ากี่วันก่อนแต้มจะหมดอายุ",
    )

    class Meta:
        verbose_name = "ตั้งค่าระบบสะสมแต้ม"
        verbose_name_plural = "ตั้งค่าระบบสะสมแต้ม"

    def save(self, *args, **kwargs):
        self.pk = 1  # บังคับให้เป็น singleton เสมอ
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # ห้ามลบ

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class PointTransaction(models.Model):
    class TxType(models.TextChoices):
        EARN = "earn", "ได้รับแต้ม"
        REDEEM = "redeem", "แลกแต้ม"
        EXPIRE = "expire", "แต้มหมดอายุ"
        ADJUST = "adjust", "ปรับปรุงแต้ม (แอดมิน)"

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE, related_name="transactions"
    )
    store = models.ForeignKey(
        "customers.Store", on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions"
    )

    tx_type = models.CharField(max_length=10, choices=TxType.choices)
    purchase_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    points = models.IntegerField(help_text="ค่าบวก = ได้แต้ม, ค่าลบ = แลก/หมดอายุ/หัก")
    balance_after = models.IntegerField()

    note = models.CharField(max_length=255, blank=True)

    # ใช้เฉพาะรายการที่ tx_type = earn เพื่อติดตามวันหมดอายุ และแต้มคงเหลือของก้อนนี้
    expire_date = models.DateField(null=True, blank=True, db_index=True)
    remaining_points = models.IntegerField(
        null=True, blank=True,
        help_text="เฉพาะรายการ earn: แต้มจากก้อนนี้ที่ยังไม่ถูกใช้/หมดอายุ (สำหรับ FIFO redemption)",
    )
    expired_notified = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["tx_type", "expire_date"]),
        ]

    def __str__(self):
        return f"{self.customer} {self.get_tx_type_display()} {self.points:+d}"

from datetime import timedelta
from decimal import Decimal, ROUND_DOWN

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from customers.models import Customer, StaffProfile
from points.models import PointBatch, PointTransaction


class InsufficientPointsError(Exception):
    pass


def calculate_points_from_amount(amount: Decimal) -> int:
    """
    กติกาข้อ 1: ทุกยอดใช้จ่าย BAHT_PER_POINT บาท = 1 คะแนน (ปัดเศษลง, ไม่ปัดขึ้นให้ลูกค้า)
    ตัวอย่าง BAHT_PER_POINT=50: ซื้อ 149 บาท -> 149 // 50 = 2 คะแนน
    """
    baht_per_point = Decimal(settings.BAHT_PER_POINT)
    points = (Decimal(amount) / baht_per_point).to_integral_value(rounding=ROUND_DOWN)
    return max(int(points), 0)


@transaction.atomic
def award_points(*, customer: Customer, purchase_amount: Decimal, staff: StaffProfile, note: str = "") -> PointTransaction:
    """
    กติกาข้อ 2: พนักงานสแกน QR ลูกค้า -> กรอกยอดซื้อ -> กดให้คะแนน
    สร้าง PointTransaction (EARN) + PointBatch ที่มีวันหมดอายุของตัวเอง
    แล้วส่ง LINE notification สรุปยอดคะแนนปัจจุบัน (กติกาข้อ 4)
    """
    points_earned = calculate_points_from_amount(purchase_amount)
    if points_earned <= 0:
        raise ValueError("ยอดซื้อไม่ถึงเกณฑ์ขั้นต่ำสำหรับรับคะแนน")

    txn = PointTransaction.objects.create(
        customer=customer,
        kind=PointTransaction.Kind.EARN,
        points=points_earned,
        purchase_amount=purchase_amount,
        staff=staff,
        note=note,
    )
    expires_at = timezone.now() + timedelta(days=settings.POINT_EXPIRY_DAYS)
    PointBatch.objects.create(
        customer=customer,
        origin_transaction=txn,
        earned_points=points_earned,
        remaining_points=points_earned,
        expires_at=expires_at,
    )

    # ส่งแจ้งเตือนหลัง commit สำเร็จ เพื่อไม่ยิง LINE ถ้า DB rollback
    transaction.on_commit(lambda: _send_points_earned_notification(customer, points_earned, expires_at))

    return txn


@transaction.atomic
def redeem_points(*, customer: Customer, points_to_redeem: int, staff: StaffProfile | None = None, note: str = "") -> PointTransaction:
    """
    ตัดแต้มแบบ FIFO จากก้อน (PointBatch) ที่ใกล้หมดอายุที่สุดก่อน
    """
    if points_to_redeem <= 0:
        raise ValueError("จำนวนแต้มที่แลกต้องมากกว่า 0")

    balance = customer.current_point_balance
    if balance < points_to_redeem:
        raise InsufficientPointsError(f"แต้มไม่พอ: มี {balance} ต้องการแลก {points_to_redeem}")

    remaining_to_deduct = points_to_redeem
    batches = (
        PointBatch.objects.select_for_update()
        .filter(customer=customer, is_expired=False, remaining_points__gt=0)
        .order_by("expires_at")
    )
    for batch in batches:
        if remaining_to_deduct <= 0:
            break
        deduct = min(batch.remaining_points, remaining_to_deduct)
        batch.remaining_points = F("remaining_points") - deduct
        batch.save(update_fields=["remaining_points"])
        remaining_to_deduct -= deduct

    txn = PointTransaction.objects.create(
        customer=customer,
        kind=PointTransaction.Kind.REDEEM,
        points=-points_to_redeem,
        staff=staff,
        note=note,
    )
    return txn


@transaction.atomic
def expire_due_batches() -> int:
    """
    เรียกจาก Celery periodic task: หา PointBatch ที่ expires_at ผ่านไปแล้วแต่ยังไม่ถูก mark
    หักออกจากยอดคงเหลือ พร้อมบันทึกเป็น PointTransaction(kind=EXPIRE) เพื่อขึ้นในประวัติ
    """
    now = timezone.now()
    due_batches = PointBatch.objects.select_for_update().filter(is_expired=False, expires_at__lte=now, remaining_points__gt=0)
    count = 0
    for batch in due_batches:
        expired_amount = batch.remaining_points
        PointTransaction.objects.create(
            customer=batch.customer,
            kind=PointTransaction.Kind.EXPIRE,
            points=-expired_amount,
            note=f"คะแนนจากรายการวันที่ {batch.earned_at:%Y-%m-%d} หมดอายุ",
        )
        batch.remaining_points = 0
        batch.is_expired = True
        batch.save(update_fields=["remaining_points", "is_expired"])
        count += 1
    return count


def get_expiring_soon(customer: Customer, within_days: int | None = None):
    """คะแนนที่กำลังจะหมดอายุภายใน N วัน (กติกาข้อ 3 และ 4)"""
    within_days = within_days or settings.EXPIRY_WARNING_DAYS
    cutoff = timezone.now() + timedelta(days=within_days)
    return PointBatch.objects.filter(
        customer=customer, is_expired=False, remaining_points__gt=0, expires_at__lte=cutoff
    ).order_by("expires_at")


def _send_points_earned_notification(customer: Customer, points_earned: int, batch_expires_at):
    """แยกออกมาเพื่อให้ tasks.py และ services.py เรียกใช้ร่วมกันได้ (import ภายในฟังก์ชันกันวน import)"""
    from line_integration.client import send_points_earned_message

    send_points_earned_message(customer=customer, points_earned=points_earned, batch_expires_at=batch_expires_at)

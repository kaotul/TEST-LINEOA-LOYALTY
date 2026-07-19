from datetime import timedelta
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import PointTransaction, PointsSetting


class InsufficientPointsError(Exception):
    pass


def calculate_points(purchase_amount: Decimal, baht_per_point: Decimal) -> int:
    """คำนวณแต้มจากยอดซื้อ: floor(purchase_amount / baht_per_point)"""
    if baht_per_point <= 0:
        return 0
    return int((Decimal(purchase_amount) / Decimal(baht_per_point)).quantize(Decimal("1"), rounding=ROUND_DOWN))


def get_balance(customer) -> int:
    total = PointTransaction.objects.filter(customer=customer).aggregate(total=Sum("points"))["total"]
    return total or 0


@transaction.atomic
def award_points(*, customer, purchase_amount: Decimal, store=None, staff=None, note=""):
    """
    ให้แต้มลูกค้าตามยอดซื้อ ตามอัตราส่วนที่ตั้งไว้ใน PointsSetting
    เรียกจากหน้า POS เมื่อพนักงานสแกน QR ลูกค้าแล้วกรอกยอดซื้อ
    """
    setting = PointsSetting.get_solo()
    points = calculate_points(purchase_amount, setting.baht_per_point)
    if points <= 0:
        raise ValueError("ยอดซื้อไม่ถึงเกณฑ์ขั้นต่ำสำหรับรับแต้ม 1 คะแนน")

    expire_date = (timezone.now() + timedelta(days=setting.point_expiry_days)).date()
    new_balance = get_balance(customer) + points

    tx = PointTransaction.objects.create(
        customer=customer,
        store=store,
        staff=staff,
        tx_type=PointTransaction.TxType.EARN,
        purchase_amount=purchase_amount,
        points=points,
        balance_after=new_balance,
        expire_date=expire_date,
        remaining_points=points,
        note=note,
    )
    return tx


@transaction.atomic
def redeem_points(*, customer, points_to_redeem: int, store=None, staff=None, note=""):
    """
    แลกแต้ม โดยตัดจากก้อนที่ใกล้หมดอายุที่สุดก่อน (FIFO ตาม expire_date)
    """
    if points_to_redeem <= 0:
        raise ValueError("จำนวนแต้มที่แลกต้องมากกว่า 0")

    current_balance = get_balance(customer)
    if points_to_redeem > current_balance:
        raise InsufficientPointsError("แต้มคงเหลือไม่เพียงพอ")

    remaining_to_deduct = points_to_redeem
    earn_txs = (
        PointTransaction.objects.select_for_update()
        .filter(customer=customer, tx_type=PointTransaction.TxType.EARN, remaining_points__gt=0)
        .order_by("expire_date", "created_at")
    )
    for earn_tx in earn_txs:
        if remaining_to_deduct <= 0:
            break
        deduct = min(earn_tx.remaining_points, remaining_to_deduct)
        earn_tx.remaining_points -= deduct
        earn_tx.save(update_fields=["remaining_points"])
        remaining_to_deduct -= deduct

    new_balance = current_balance - points_to_redeem
    tx = PointTransaction.objects.create(
        customer=customer,
        store=store,
        staff=staff,
        tx_type=PointTransaction.TxType.REDEEM,
        points=-points_to_redeem,
        balance_after=new_balance,
        note=note,
    )
    return tx


def get_expiring_soon(customer, within_days: int):
    """คืนแต้มที่จะหมดอายุภายใน N วันข้างหน้า (สำหรับแสดงผล/แจ้งเตือน)"""
    today = timezone.now().date()
    cutoff = today + timedelta(days=within_days)
    qs = PointTransaction.objects.filter(
        customer=customer,
        tx_type=PointTransaction.TxType.EARN,
        remaining_points__gt=0,
        expire_date__gte=today,
        expire_date__lte=cutoff,
    ).order_by("expire_date")
    total = qs.aggregate(total=Sum("remaining_points"))["total"] or 0
    return qs, total

from celery import shared_task
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import PointTransaction, PointsSetting
from .services import get_balance, get_expiring_soon


@shared_task
def expire_due_points():
    """
    รันทุกวัน: หาแต้ม (earn) ที่ expire_date < วันนี้ และยังมี remaining_points > 0
    แล้วสร้างรายการ 'expire' หักออกจากยอดคงเหลือ
    """
    from apps.customers.models import Customer

    today = timezone.now().date()
    customer_ids = (
        PointTransaction.objects.filter(
            tx_type=PointTransaction.TxType.EARN,
            remaining_points__gt=0,
            expire_date__lt=today,
        )
        .values_list("customer_id", flat=True)
        .distinct()
    )

    for customer_id in customer_ids:
        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(id=customer_id)
            expired_txs = PointTransaction.objects.select_for_update().filter(
                customer=customer,
                tx_type=PointTransaction.TxType.EARN,
                remaining_points__gt=0,
                expire_date__lt=today,
            )
            total_expired = expired_txs.aggregate(total=Sum("remaining_points"))["total"] or 0
            if total_expired <= 0:
                continue

            for tx in expired_txs:
                tx.remaining_points = 0
                tx.save(update_fields=["remaining_points"])

            new_balance = get_balance(customer) - total_expired
            PointTransaction.objects.create(
                customer=customer,
                tx_type=PointTransaction.TxType.EXPIRE,
                points=-total_expired,
                balance_after=new_balance,
                note=f"แต้มหมดอายุอัตโนมัติ ({total_expired} แต้ม)",
            )


@shared_task
def notify_expiring_points():
    """รันทุกวัน: แจ้งเตือนลูกค้าที่มีแต้มใกล้หมดอายุภายใน expiry_warning_days วัน"""
    from apps.customers.models import Customer
    from apps.lineoa.services import push_text_message
    from apps.lineoa.messages import build_expiry_warning_message

    setting = PointsSetting.get_solo()
    customers = Customer.objects.filter(is_active=True)

    for customer in customers:
        _qs, total_expiring = get_expiring_soon(customer, setting.expiry_warning_days)
        if total_expiring <= 0:
            continue
        balance = get_balance(customer)
        message = build_expiry_warning_message(
            balance=balance, expiring_points=total_expiring, days=setting.expiry_warning_days
        )
        push_text_message(customer.line_user_id, message)


@shared_task
def notify_points_earned(transaction_id):
    """แจ้งเตือนทันทีหลังลูกค้าได้รับแต้ม (เรียกจาก POS view หลัง award_points สำเร็จ)"""
    from apps.lineoa.services import push_text_message
    from apps.lineoa.messages import build_earn_notification_message

    tx = PointTransaction.objects.select_related("customer").get(id=transaction_id)
    setting = PointsSetting.get_solo()
    balance = get_balance(tx.customer)
    _qs, expiring_soon = get_expiring_soon(tx.customer, setting.expiry_warning_days)

    message = build_earn_notification_message(
        earned_points=tx.points,
        purchase_amount=tx.purchase_amount,
        balance=balance,
        expire_date=tx.expire_date,
        expiring_soon=expiring_soon,
    )
    push_text_message(tx.customer.line_user_id, message)

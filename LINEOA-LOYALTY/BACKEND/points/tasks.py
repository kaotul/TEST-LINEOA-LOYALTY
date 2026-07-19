from celery import shared_task
from django.conf import settings
from django.utils import timezone

from customers.models import Customer


@shared_task
def expire_due_points():
    """รันทุกชั่วโมง: หักแต้มที่หมดอายุแล้วออกจากยอดคงเหลือ"""
    from points.services import expire_due_batches

    count = expire_due_batches()
    return f"Expired {count} point batches"


@shared_task
def notify_expiring_points():
    """
    รันทุกวัน: แจ้งเตือนลูกค้าทุกคนที่มีคะแนนใกล้หมดอายุภายใน EXPIRY_WARNING_DAYS วัน
    (กติกาข้อ 4 - ส่วน 'คะแนนที่กำลังจะหมดอายุ')
    """
    from line_integration.client import send_expiry_warning_message
    from points.services import get_expiring_soon

    notified = 0
    for customer in Customer.objects.filter(is_active=True):
        expiring_batches = get_expiring_soon(customer)
        if not expiring_batches.exists():
            continue
        total_expiring = sum(b.remaining_points for b in expiring_batches)
        nearest_expiry = expiring_batches.first().expires_at
        send_expiry_warning_message(customer=customer, expiring_points=total_expiring, expires_at=nearest_expiry)
        notified += 1
    return f"Notified {notified} customers about expiring points"

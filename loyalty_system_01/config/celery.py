import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("loyalty_system")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ตารางงานประจำ (ตั้งซ้ำผ่าน django-celery-beat ใน admin ได้เช่นกัน)
app.conf.beat_schedule = {
    "expire-points-daily": {
        "task": "points.tasks.expire_due_points",
        "schedule": 60 * 60,  # ทุก 1 ชั่วโมง เช็คแต้มที่ถึงกำหนดหมดอายุ
    },
    "warn-expiring-points-daily": {
        "task": "points.tasks.notify_expiring_points",
        "schedule": 60 * 60 * 24,  # ทุกวัน แจ้งเตือนแต้มที่ใกล้หมดอายุ
    },
}

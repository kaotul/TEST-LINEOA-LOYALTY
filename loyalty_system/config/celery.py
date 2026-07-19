import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("loyalty_system")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "expire-points-daily": {
        "task": "apps.loyalty.tasks.expire_due_points",
        "schedule": crontab(hour=1, minute=0),  # 01:00 ทุกวัน
    },
    "notify-expiring-points-daily": {
        "task": "apps.loyalty.tasks.notify_expiring_points",
        "schedule": crontab(hour=9, minute=0),  # 09:00 ทุกวัน
    },
}

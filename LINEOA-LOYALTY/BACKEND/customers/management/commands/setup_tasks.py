import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule

logger = logging.getLogger(__name__)


def get_next_month_first_day():
    """คำนวณวันเวลาของวันที่ 1 ในเดือนถัดไป เวลา 00:00 น."""
    now = timezone.now()
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1, 0, 0, 0)
    else:
        next_month = datetime(now.year, now.month + 1, 1, 0, 0, 0)

    # หากระบบใช้ Timezone ให้สร้างเป็น Aware Datetime
    if timezone.is_aware(now):
        return timezone.make_aware(next_month)
    return next_month


class Command(BaseCommand):
    help = "สร้าง/ตั้งค่า Scheduled Tasks สำหรับระบบ (Delete Old Images และ Keep Latest Sequences)"

    def handle(self, *args, **options):
        # -------------------------------------------------------------
        # 1. Task: ลบรูปภาพเก่า (รันทุกๆ 1 ชั่วโมง)
        # -------------------------------------------------------------
        task_1_name = "Delete Old Images Schedule"
        schedule_1, created_1 = Schedule.objects.update_or_create(
            name=task_1_name,
            defaults={
                "func": "django.core.management.call_command",
                "args": "'delete_old_images', 1440",
                "schedule_type": Schedule.HOURLY,  # รันทุกๆ 1 ชั่วโมง
                "repeats": -1,  # รันไปเรื่อยๆ ไม่มีวันสิ้นสุด
            },
        )
        self._log_status(task_1_name, created_1)

        # -------------------------------------------------------------
        # 2. Task: ลบ Sequence เก่าเก็บไว้เฉพาะ 30 รายการล่าสุด (รันทุกวันที่ 1 ของเดือน)
        # -------------------------------------------------------------
        task_2_name = "Delete Old Sequences Schedule"

        # คำนวณวันรันครั้งถัดไปให้เริ่มวันที่ 1 ของเดือนถัดไป เวลา 00:00 น.
        next_first_day = get_next_month_first_day()

        schedule_2, created_2 = Schedule.objects.update_or_create(
            name=task_2_name,
            defaults={
                # เรียกใช้ django.core.management.call_command('delete_old_sequences', keep=30)
                "func": "django.core.management.call_command",
                "args": "'delete_old_sequences'",
                "kwargs": "{'keep': 30}",  # ส่ง --keep 30 เป็น kwargs
                "schedule_type": Schedule.MONTHLY,  # รันเดือนละ 1 ครั้ง
                "next_run": next_first_day,  # เริ่มรันวันที่ 1 ของเดือน
                "repeats": -1,
            },
        )
        self._log_status(task_2_name, created_2)

        # -------------------------------------------------------------
        # 3. Task: ลบ drf_api_logs เก่าเก็บไว้เฉพาะ 60 รายการล่าสุด (รันทุกวันที่ 1 ของเดือน)
        # -------------------------------------------------------------
        task_3_name = "Delete_old_api_logs_monthly"

        # คำนวณวันรันครั้งถัดไปให้เริ่มวันที่ 1 ของเดือนถัดไป เวลา 00:00 น.
        next_first_day = get_next_month_first_day()

        schedule_3, created_3 = Schedule.objects.update_or_create(
            name=task_3_name,
            defaults={
                # เรียกใช้ django.core.management.call_command('delete_old_logs', days=30)
                "func": "django.core.management.call_command",
                "args": "'delete_old_logs'",
                "kwargs": "{'days': 60}",  # ส่ง --days 30 เป็น kwargs
                "schedule_type": Schedule.MONTHLY,  # รันเดือนละ 1 ครั้ง
                "next_run": next_first_day,  # เริ่มรันวันที่ 1 ของเดือน
                "repeats": -1,
            },
        )
        self._log_status(task_3_name, created_3)


    def _log_status(self, task_name, created):
        status = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(f'Successfully {status} schedule: "{task_name}"')
        )
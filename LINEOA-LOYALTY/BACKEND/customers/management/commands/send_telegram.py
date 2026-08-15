import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "ส่งข้อความแจ้งเตือนไปยัง Telegram Chat"

    def add_arguments(self, parser):
        # รับข้อความที่ต้องการส่งผ่าน Command Line
        parser.add_argument(
            "message", type=str, help="ข้อความที่ต้องการส่งไปยัง Telegram"
        )

        # (Optional) ตัวเลือกสำหรับเปลี่ยน Chat ID แบบไดนามิก
        parser.add_argument(
            "--chat_id", type=str, help="Chat ID ปลายทาง (ถ้าไม่ระบุจะใช้ค่า default)"
        )

    def handle(self, *args, **options):
        # ดึงค่า Token / Chat ID จาก settings.py หรือจาก Argument
        bot_token = getattr(
            settings, "TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE"
        )
        chat_id = (
            options["chat_id"]
            or getattr(settings, "TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")
        )
        message = options["message"]

        if not bot_token or bot_token == "YOUR_BOT_TOKEN_HERE":
            raise CommandError("กรุณาตั้งค่า TELEGRAM_BOT_TOKEN ก่อนใช้งาน")

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",  # รองรับการใช้ <b>ตัวหนา</b> <i>ตัวเอียง</i>
        }

        try:
            response = requests.post(url, data=payload, timeout=10)
            data = response.json()

            if response.status_code == 200 and data.get("ok"):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"ส่งข้อความสำเร็จ! (Message ID: {data['result']['message_id']})"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"ส่งไม่สำเร็จ: {data.get('description')}"
                    )
                )

        except requests.RequestException as e:
            raise CommandError(f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
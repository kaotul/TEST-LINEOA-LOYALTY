from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.lineoa.services import create_rich_menu, upload_rich_menu_image, set_default_rich_menu


class Command(BaseCommand):
    help = (
        "สร้างและตั้งค่า Rich Menu บน LINE OA (ปุ่ม: คะแนนของฉัน / ประวัติ / QR รับแต้ม)\n"
        "ใช้งาน: python manage.py setup_rich_menu --image /path/to/richmenu.png"
    )

    def add_arguments(self, parser):
        parser.add_argument("--image", required=True, help="พาธไฟล์รูป Rich Menu ขนาด 2500x1686 px")

    def handle(self, *args, **options):
        liff_id = settings.LIFF_ID
        if not liff_id:
            raise CommandError("กรุณาตั้งค่า LIFF_ID ใน .env ก่อน")

        rich_menu_object = {
            "size": {"width": 2500, "height": 1686},
            "selected": True,
            "name": "Loyalty Main Menu",
            "chatBarText": "เมนูสมาชิก",
            "areas": [
                {
                    "bounds": {"x": 0, "y": 0, "width": 833, "height": 1686},
                    "action": {"type": "uri", "label": "คะแนนของฉัน", "uri": f"https://liff.line.me/{liff_id}"},
                },
                {
                    "bounds": {"x": 833, "y": 0, "width": 834, "height": 1686},
                    "action": {
                        "type": "uri",
                        "label": "ประวัติ",
                        "uri": f"https://liff.line.me/{liff_id}?page=history",
                    },
                },
                {
                    "bounds": {"x": 1667, "y": 0, "width": 833, "height": 1686},
                    "action": {
                        "type": "uri",
                        "label": "QR รับแต้ม",
                        "uri": f"https://liff.line.me/{liff_id}?page=qrcode",
                    },
                },
            ],
        }

        rich_menu_id = create_rich_menu(rich_menu_object)
        if not rich_menu_id:
            raise CommandError("สร้าง Rich Menu ไม่สำเร็จ ตรวจสอบ LINE_CHANNEL_ACCESS_TOKEN")

        with open(options["image"], "rb") as f:
            image_bytes = f.read()

        if not upload_rich_menu_image(rich_menu_id, image_bytes):
            raise CommandError("อัปโหลดรูป Rich Menu ไม่สำเร็จ")

        if not set_default_rich_menu(rich_menu_id):
            raise CommandError("ตั้ง Rich Menu เป็นค่าเริ่มต้นไม่สำเร็จ")

        self.stdout.write(self.style.SUCCESS(f"ตั้งค่า Rich Menu สำเร็จ: {rich_menu_id}"))

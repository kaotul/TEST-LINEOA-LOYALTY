"""
รันครั้งเดียว (หรือทุกครั้งที่ต้องการอัปเดตเมนู):
    python manage.py setup_richmenu --image path/to/richmenu.png

สร้าง Rich Menu ที่มีปุ่ม "คะแนนของฉัน" เปิด LIFF (กติกาข้อ 3) แล้วตั้งเป็นเมนูเริ่มต้นของทุกคนที่แชทกับ OA
รูปภาพต้องมีขนาด 2500x1686 หรือ 2500x843 px ตามสเปกของ LINE
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    MessagingApiBlob,
    RichMenuArea,
    RichMenuBounds,
    RichMenuRequest,
    RichMenuSize,
    URIAction,
)


class Command(BaseCommand):
    help = "สร้างและตั้งค่า Rich Menu สำหรับระบบสะสมคะแนนบน LINE OA"

    def add_arguments(self, parser):
        parser.add_argument("--image", required=True, help="path ไฟล์รูป Rich Menu (PNG/JPEG, 2500x1686 หรือ 2500x843)")

    def handle(self, *args, **options):
        if not settings.LINE_CHANNEL_ACCESS_TOKEN:
            raise CommandError("ยังไม่ได้ตั้งค่า LINE_CHANNEL_ACCESS_TOKEN ใน .env")

        config = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
        with ApiClient(config) as api_client:
            api = MessagingApi(api_client)
            blob_api = MessagingApiBlob(api_client)

            liff_url = f"{settings.LIFF_BASE_URL}/{settings.LIFF_ID}"

            rich_menu_request = RichMenuRequest(
                size=RichMenuSize(width=2500, height=843),
                selected=True,
                name="loyalty-main-menu",
                chat_bar_text="เมนู",
                areas=[
                    RichMenuArea(
                        bounds=RichMenuBounds(x=0, y=0, width=1250, height=843),
                        action=URIAction(label="คะแนนของฉัน", uri=liff_url),
                    ),
                    RichMenuArea(
                        bounds=RichMenuBounds(x=1250, y=0, width=1250, height=843),
                        action=URIAction(label="ติดต่อร้าน", uri="https://line.me/R/ti/p/@your-oa-id"),
                    ),
                ],
            )

            rich_menu_id = api.create_rich_menu(rich_menu_request).rich_menu_id
            self.stdout.write(f"สร้าง Rich Menu แล้ว: {rich_menu_id}")

            with open(options["image"], "rb") as f:
                blob_api.set_rich_menu_image(rich_menu_id, body=f.read(), _headers={"Content-Type": "image/png"})
            self.stdout.write("อัปโหลดรูปภาพสำเร็จ")

            api.set_default_rich_menu(rich_menu_id)
            self.stdout.write(self.style.SUCCESS(f"ตั้งเป็นเมนูเริ่มต้นเรียบร้อย: {rich_menu_id}"))

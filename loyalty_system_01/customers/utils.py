import io

import qrcode
from django.core.files.base import ContentFile


def generate_qr_png(qr_token) -> ContentFile:
    """
    สร้างรูป QR Code (PNG) จาก qr_token ของลูกค้า
    เนื้อหาใน QR คือ URL ภายใน (เช่น pos://scan/<token> หรือ plain token string)
    ในที่นี้ใช้ deep-link string ธรรมดา ให้หน้า POS (JS scanner) parse เอา token ออกมา
    """
    payload = f"LOYALTY-QR:{qr_token}"
    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ContentFile(buf.read(), name=f"qr_{qr_token}.png")

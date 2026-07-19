import io
import base64
import qrcode


def generate_qr_base64(payload: str) -> str:
    """สร้าง QR Code เป็น base64 PNG (ฝัง <img src='data:image/png;base64,...'> ได้ทันที)"""
    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")

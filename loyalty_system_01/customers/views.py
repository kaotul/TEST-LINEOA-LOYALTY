import io

import qrcode
import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view
from rest_framework.response import Response

from points.models import PointTransaction
from points.services import get_expiring_soon

from .models import Customer
from .serializers import CustomerSummarySerializer


def _verify_liff_id_token(id_token: str) -> str | None:
    """
    ตรวจสอบ LIFF ID token กับ LINE โดยตรง (server-side) เพื่อยืนยันว่าเป็นผู้ใช้ LINE จริง
    ก่อนคืนข้อมูลคะแนนที่ผูกกับ line_user_id นั้น ป้องกันการปลอม userId จากฝั่ง client
    คืนค่า line_user_id ถ้า token ถูกต้อง, None ถ้าไม่ถูกต้อง
    """
    liff_channel_id = settings.LIFF_CHANNEL_ID
    try:
        resp = requests.post(
            "https://api.line.me/oauth2/v2.1/verify",
            data={"id_token": id_token, "client_id": liff_channel_id},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("sub")
    except requests.RequestException:
        return None


@api_view(["GET"])
def my_points_summary(request):
    """
    GET /api/liff/me/?id_token=<LIFF ID Token>
    ใช้โดยหน้า LIFF (กติกาข้อ 3): คะแนนรวม, ประวัติรับ-แลก, วันหมดอายุ
    """
    id_token = request.query_params.get("id_token")
    if not id_token:
        return Response({"detail": "id_token is required"}, status=400)

    line_user_id = _verify_liff_id_token(id_token)
    if not line_user_id:
        return Response({"detail": "invalid id_token"}, status=401)

    customer = get_object_or_404(Customer, line_user_id=line_user_id, is_active=True)

    expiring = get_expiring_soon(customer)
    expiring_total = sum(b.remaining_points for b in expiring)
    nearest = expiring.first()

    data = {
        "display_name": customer.display_name,
        "total_points": customer.current_point_balance,
        "qr_token": customer.qr_token,
        "nearest_expiry": nearest.expires_at if nearest else None,
        "expiring_soon_points": expiring_total,
        "history": customer.transactions.all()[:50],
        "expiring_batches": expiring,
    }
    return Response(CustomerSummarySerializer(data).data)


@require_GET
def customer_qr_image(request, qr_token):
    """
    GET /qr/<qr_token>.png
    คืนรูป QR Code ของลูกค้า (ให้ลูกค้าโชว์หน้าจอมือถือให้พนักงานสแกน)
    สร้างแบบ on-the-fly ไม่ต้องเก็บไฟล์ถาวร
    """
    customer = get_object_or_404(Customer, qr_token=qr_token, is_active=True)
    payload = f"LOYALTY-QR:{customer.qr_token}"
    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")

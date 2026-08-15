import io

import qrcode
import requests
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view
from rest_framework.response import Response

from points.services import get_expiring_soon

from .models import Customer
from .serializers import CustomerSummarySerializer
import logging

logger = logging.getLogger('CORE')

def _verify_liff_id_token(id_token: str) -> dict | None:
    """
    ตรวจสอบ LIFF ID token กับ LINE โดยตรง (server-side, ส่วนหนึ่งของ LINE Login - กติกาข้อ 1)
    เพื่อยืนยันว่าเป็นผู้ใช้ LINE จริงก่อนสร้าง/คืนข้อมูลสมาชิก ป้องกันการปลอม userId จากฝั่ง client
    คืนค่า dict payload ของ token (มี sub=userId, name, picture ถ้า scope มี profile) หรือ None ถ้าไม่ผ่าน
    """
    channel_id = getattr(settings, "LIFF_CHANNEL_ID", None)
    logger.info(f"Verifying LIFF ID token with LINE: channel_id={channel_id}, id_token={id_token}")

    try:
        resp = requests.post(
            "https://api.line.me/oauth2/v2.1/verify",
            data={"id_token": id_token, "client_id": channel_id},
            timeout=5,
        )
        if resp.status_code != 200:
            logger.warning(f"Failed to verify LIFF ID token: {resp.status_code}")
            return None
        return resp.json()
    except requests.RequestException:
        return None


@api_view(["POST"])
def register_or_login(request):
    """
    POST /customers/api/liff/register/
    body: {id_token, phone_number?, display_name?, consent_accepted}

    ขั้นตอน "ลงทะเบียน หรือ login ผ่านระบบ LINE OA" (กติกาข้อ 1):
    - ตรวจ id_token กับ LINE (เทียบเท่า LINE Login) เพื่อยืนยันตัวตน
    - ถ้ายังไม่มี Customer -> สร้างใหม่ (สมัครสมาชิก)
    - ถ้ามีอยู่แล้ว -> อัปเดตข้อมูล/ทำเครื่องหมาย login (อัปเดต updated_at) แล้วคืนสถานะสมาชิก
    - ต้องกด "ยอมรับเงื่อนไข" (consent_accepted=True) ในการสมัครครั้งแรก ระบบถึงจะปลด is_registered=True
      และเริ่มใช้งานคะแนน/QR ได้เต็มรูปแบบ
    """
    id_token = request.data.get("id_token")
    if not id_token:
        return Response({"detail": "id_token is required"}, status=400)

    payload = _verify_liff_id_token(id_token)
    if not payload or not payload.get("sub"):
        return Response({"detail": "invalid id_token"}, status=401)

    logger.info(f"LIFF ID token verified: sub={payload['sub']}, name={payload.get('name')}, picture={payload.get('picture')}")
    line_user_id = payload["sub"]
    customer, created = Customer.objects.get_or_create(
        line_user_id=line_user_id,
        defaults={
            "display_name": payload.get("name", ""),
            "picture_url": payload.get("picture", ""),
        },
    )

    consent_accepted = bool(request.data.get("consent_accepted"))
    phone_number = request.data.get("phone_number", "").strip()
    display_name = request.data.get("display_name", "").strip()

    if not customer.is_registered:
        # ขั้นตอนสมัครสมาชิกครั้งแรก: ต้องกรอกเบอร์โทรและยอมรับเงื่อนไขก่อนถึงจะลงทะเบียนสำเร็จ
        if not consent_accepted or not phone_number:
            return Response({
                "registered": False,
                "detail": "กรุณากรอกเบอร์โทรศัพท์และยอมรับเงื่อนไขเพื่อสมัครสมาชิก",
                "display_name": customer.display_name or payload.get("name", ""),
                "picture_url": customer.picture_url or payload.get("picture", ""),
            }, status=200)

        customer.phone_number = phone_number
        customer.display_name = display_name or customer.display_name or payload.get("name", "")
        customer.consent_accepted = True
        customer.is_registered = True
        customer.registered_at = timezone.now()
        customer.is_active = True
        customer.save()
    else:
        # "login" ซ้ำ: แค่ sync ชื่อ/รูปล่าสุดจาก LINE เผื่อลูกค้าเปลี่ยนโปรไฟล์
        updated_fields = []
        if payload.get("name") and payload["name"] != customer.display_name:
            customer.display_name = payload["name"]
            updated_fields.append("display_name")
        if payload.get("picture") and payload["picture"] != customer.picture_url:
            customer.picture_url = payload["picture"]
            updated_fields.append("picture_url")
        if updated_fields:
            customer.save(update_fields=updated_fields)

    return Response({
        "registered": customer.is_registered,
        "display_name": customer.display_name,
        "qr_token": customer.qr_token,
        "total_points": customer.current_point_balance,
    })


@api_view(["GET"])
def my_points_summary(request):
    """
    GET /customers/api/liff/me/?id_token=<LIFF ID Token>
    ใช้โดยหน้า LIFF (กติกาข้อ 4): คะแนนรวม, ประวัติรับ-แลก, วันหมดอายุ
    ต้องผ่านการลงทะเบียน (is_registered=True) แล้วเท่านั้น ไม่งั้นตอบ 428 ให้ front-end พาไปหน้าสมัครสมาชิกก่อน
    """
    id_token = request.query_params.get("id_token")
    logger.info(f"Fetching points summary for LIFF ID token: {id_token}")

    if not id_token:
        return Response({"detail": "id_token is required"}, status=400)

    payload = _verify_liff_id_token(id_token)
    if not payload or not payload.get("sub"):
        return Response({"detail": "invalid id_token"}, status=401)

    logger.info(f'Customer ID token verified: sub={payload["sub"]}, name={payload.get("name")}, picture={payload.get("picture")}')
    customer = get_object_or_404(Customer, line_user_id=payload["sub"], is_active=True)
    if not customer.is_registered:
        logger.warning(f"Customer {customer.id} is not registered yet")
        return Response({"detail": "customer not registered", "registered": False}, status=428)

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
    logger.info(f"Returning points summary for customer {customer.id}: {data}")
    return Response(CustomerSummarySerializer(data).data)


@require_GET
def customer_qr_image(request, qr_token):
    """
    GET /customers/qr/<qr_token>.png
    คืนรูป QR Code ของลูกค้า (ให้ลูกค้าโชว์หน้าจอมือถือให้พนักงานสแกน) เฉพาะสมาชิกที่ลงทะเบียนแล้ว
    สร้างแบบ on-the-fly ไม่ต้องเก็บไฟล์ถาวร
    """
    customer = get_object_or_404(Customer, qr_token=qr_token, is_active=True, is_registered=True)
    payload = f"LOYALTY-QR:{customer.qr_token}"
    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")

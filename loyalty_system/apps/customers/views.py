import json
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Customer
from .utils import generate_qr_base64
from apps.lineoa.services import verify_line_id_token


def liff_index(request):
    """หน้าแรกของ LIFF app — แสดงคะแนนรวม (ข้อมูลจริงโหลดผ่าน JS/API หลัง login)"""
    return render(request, "liff/index.html", {"liff_id": settings.LIFF_ID})


def liff_history(request):
    return render(request, "liff/history.html", {"liff_id": settings.LIFF_ID})


@csrf_exempt
@require_POST
def liff_login(request):
    """
    รับ LINE ID token จาก LIFF SDK (liff.getIDToken()) ฝั่ง client,
    verify กับ LINE แล้วสร้าง/ดึงข้อมูล Customer, เก็บ customer_id ไว้ใน session
    """
    try:
        body = json.loads(request.body or "{}")
        id_token = body.get("id_token")
        if not id_token:
            return JsonResponse({"ok": False, "error": "missing id_token"}, status=400)

        claims = verify_line_id_token(id_token)
        if not claims:
            return JsonResponse({"ok": False, "error": "invalid id_token"}, status=401)

        line_user_id = claims["sub"]
        customer, _created = Customer.objects.get_or_create(
            line_user_id=line_user_id,
            defaults={
                "display_name": claims.get("name", ""),
                "picture_url": claims.get("picture", ""),
            },
        )
        # อัปเดตข้อมูลโปรไฟล์ล่าสุดทุกครั้งที่ login
        customer.display_name = claims.get("name", customer.display_name)
        customer.picture_url = claims.get("picture", customer.picture_url)
        customer.save(update_fields=["display_name", "picture_url", "last_login_at"])

        request.session["liff_customer_id"] = customer.id
        return JsonResponse({"ok": True, "customer_id": customer.id})
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


def liff_qrcode(request):
    """คืนภาพ QR Code (base64) สำหรับให้พนักงานสแกน ต้อง login (session) ก่อน"""
    customer_id = request.session.get("liff_customer_id")
    if not customer_id:
        return JsonResponse({"ok": False, "error": "not_logged_in"}, status=401)
    customer = Customer.objects.get(id=customer_id)
    return JsonResponse({
        "ok": True,
        "qr_base64": generate_qr_base64(customer.qr_payload),
        "member_code": str(customer.member_code),
    })

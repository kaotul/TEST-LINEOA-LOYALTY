from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from customers.models import Customer
from points.services import award_points, calculate_points_from_amount


@login_required
def dashboard(request):
    """
    หน้าหลักของพนักงาน (กติกาข้อ 2): เปิดกล้องสแกน QR ลูกค้า -> กรอกยอดซื้อ -> กดให้คะแนน
    ใช้ไลบรารี JS html5-qrcode ฝั่ง client แล้วยิงผลมาที่ /pos/api/lookup/ และ /pos/api/award/
    """
    return render(request, "pos/dashboard.html", {
        "staff_name": request.user.get_full_name() or request.user.username,
        "baht_per_point": settings.BAHT_PER_POINT,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lookup_customer(request):
    """
    GET /pos/api/lookup/?token=<qr_token หรือ payload ที่สแกนได้>
    รับ payload ดิบจากกล้อง (รูปแบบ 'LOYALTY-QR:<uuid>') แล้วดึงข้อมูลลูกค้ามาแสดงยืนยันก่อนให้แต้ม
    """
    raw = request.query_params.get("token", "")
    token = raw.split(":")[-1].strip() if raw else ""
    customer = get_object_or_404(Customer, qr_token=token, is_active=True)
    return Response({
        "customer_id": customer.id,
        "display_name": customer.display_name,
        "picture_url": customer.picture_url,
        "current_points": customer.current_point_balance,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def award(request):
    """
    POST /pos/api/award/  body: {customer_id, purchase_amount, note?}
    คำนวณแต้มจากยอดซื้อ (ทุก BAHT_PER_POINT บาท = 1 แต้ม) แล้วบันทึก + ส่ง LINE notification
    """
    customer_id = request.data.get("customer_id")
    amount_raw = request.data.get("purchase_amount")

    try:
        amount = Decimal(str(amount_raw))
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        return Response({"detail": "purchase_amount ไม่ถูกต้อง"}, status=400)

    customer = get_object_or_404(Customer, id=customer_id, is_active=True)
    staff_profile = getattr(request.user, "staff_profile", None)
    if staff_profile is None:
        return Response({"detail": "บัญชีนี้ไม่มีสิทธิ์พนักงาน POS"}, status=403)

    preview_points = calculate_points_from_amount(amount)
    if preview_points <= 0:
        return Response({"detail": f"ยอดซื้อไม่ถึง {amount} บาทขั้นต่ำต่อ 1 คะแนน"}, status=400)

    txn = award_points(
        customer=customer,
        purchase_amount=amount,
        staff=staff_profile,
        note=request.data.get("note", ""),
    )
    return Response({
        "points_earned": txn.points,
        "new_balance": customer.current_point_balance,
    }, status=201)

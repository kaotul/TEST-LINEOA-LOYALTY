from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages as flash
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.accounts.permissions import role_required, store_queryset_filter
from apps.customers.models import Customer
from apps.loyalty.models import PointTransaction, PointsSetting
from apps.loyalty.services import award_points, redeem_points, get_balance, InsufficientPointsError
from apps.loyalty.tasks import notify_points_earned


def login_view(request):
    if request.user.is_authenticated:
        return redirect("pos:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return redirect("pos:dashboard")
        flash.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    return render(request, "pos/login.html")


@login_required(login_url="pos:login")
def logout_view(request):
    logout(request)
    return redirect("pos:login")


@login_required(login_url="pos:login")
def dashboard(request):
    setting = PointsSetting.get_solo()
    txs = PointTransaction.objects.select_related("customer", "store", "staff")
    txs = store_queryset_filter(request.user, txs)
    return render(request, "pos/dashboard.html", {
        "setting": setting,
        "recent_transactions": txs[:20],
    })


@login_required(login_url="pos:login")
def scan_page(request):
    """หน้าสแกน QR ลูกค้า (กล้องมือถือ/เว็บแคม ผ่าน JS html5-qrcode)"""
    if not request.user.can_award_points:
        flash.error(request, "คุณไม่มีสิทธิ์ให้คะแนน")
        return redirect("pos:dashboard")
    return render(request, "pos/scan.html")


@login_required(login_url="pos:login")
@require_POST
def lookup_customer(request):
    """รับ payload จาก QR ('LOYALTY:<member_code>') แล้วคืนข้อมูลลูกค้า + แต้มคงเหลือ"""
    payload = request.POST.get("payload", "")
    member_code = payload.split("LOYALTY:")[-1].strip() if "LOYALTY:" in payload else payload.strip()

    customer = Customer.objects.filter(member_code=member_code, is_active=True).first()
    if not customer:
        return JsonResponse({"ok": False, "error": "ไม่พบข้อมูลสมาชิก"}, status=404)

    return JsonResponse({
        "ok": True,
        "customer_id": customer.id,
        "display_name": customer.display_name,
        "picture_url": customer.picture_url,
        "balance": get_balance(customer),
    })


@login_required(login_url="pos:login")
@require_POST
def award_points_view(request):
    if not request.user.can_award_points:
        return JsonResponse({"ok": False, "error": "ไม่มีสิทธิ์"}, status=403)

    customer = get_object_or_404(Customer, id=request.POST.get("customer_id"))
    try:
        purchase_amount = Decimal(request.POST.get("purchase_amount", "0"))
    except InvalidOperation:
        return JsonResponse({"ok": False, "error": "ยอดซื้อไม่ถูกต้อง"}, status=400)

    try:
        tx = award_points(
            customer=customer,
            purchase_amount=purchase_amount,
            store=request.user.store,
            staff=request.user,
            note="ให้แต้มผ่านหน้า POS",
        )
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    notify_points_earned.delay(tx.id)

    return JsonResponse({
        "ok": True,
        "points_awarded": tx.points,
        "new_balance": tx.balance_after,
        "expire_date": tx.expire_date.isoformat(),
    })


@login_required(login_url="pos:login")
@require_POST
def redeem_points_view(request):
    if not request.user.can_award_points:
        return JsonResponse({"ok": False, "error": "ไม่มีสิทธิ์"}, status=403)

    customer = get_object_or_404(Customer, id=request.POST.get("customer_id"))
    try:
        points = int(request.POST.get("points", "0"))
        tx = redeem_points(
            customer=customer, points_to_redeem=points,
            store=request.user.store, staff=request.user, note="แลกแต้มผ่านหน้า POS",
        )
    except (ValueError, InsufficientPointsError) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    return JsonResponse({"ok": True, "new_balance": tx.balance_after})


@role_required("admin")
def settings_view(request):
    setting = PointsSetting.get_solo()
    if request.method == "POST":
        try:
            setting.baht_per_point = Decimal(request.POST.get("baht_per_point"))
            setting.point_expiry_days = int(request.POST.get("point_expiry_days"))
            setting.expiry_warning_days = int(request.POST.get("expiry_warning_days"))
            setting.save()
            flash.success(request, "บันทึกการตั้งค่าเรียบร้อย")
        except (InvalidOperation, ValueError, TypeError):
            flash.error(request, "ข้อมูลไม่ถูกต้อง")
        return redirect("pos:settings")

    return render(request, "pos/settings.html", {"setting": setting})


@role_required("admin", "manager")
def reports_view(request):
    txs = PointTransaction.objects.select_related("customer", "store", "staff")
    txs = store_queryset_filter(request.user, txs)
    return render(request, "pos/reports.html", {"transactions": txs[:200]})

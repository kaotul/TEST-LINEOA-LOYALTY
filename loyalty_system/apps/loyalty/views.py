from django.http import JsonResponse

from apps.customers.models import Customer
from .models import PointTransaction, PointsSetting
from .services import get_balance, get_expiring_soon


def _current_customer(request):
    customer_id = request.session.get("liff_customer_id")
    if not customer_id:
        return None
    return Customer.objects.filter(id=customer_id).first()


def my_summary(request):
    customer = _current_customer(request)
    if not customer:
        return JsonResponse({"ok": False, "error": "not_logged_in"}, status=401)

    setting = PointsSetting.get_solo()
    balance = get_balance(customer)
    _qs, expiring_soon = get_expiring_soon(customer, setting.expiry_warning_days)

    nearest = (
        PointTransaction.objects.filter(
            customer=customer,
            tx_type=PointTransaction.TxType.EARN,
            remaining_points__gt=0,
        )
        .order_by("expire_date")
        .values_list("expire_date", flat=True)
        .first()
    )

    return JsonResponse({
        "ok": True,
        "display_name": customer.display_name,
        "picture_url": customer.picture_url,
        "balance": balance,
        "expiring_soon_points": expiring_soon,
        "expiring_soon_days": setting.expiry_warning_days,
        "nearest_expiry_date": nearest.isoformat() if nearest else None,
    })


def my_history(request):
    customer = _current_customer(request)
    if not customer:
        return JsonResponse({"ok": False, "error": "not_logged_in"}, status=401)

    txs = PointTransaction.objects.filter(customer=customer)[:100]
    data = [
        {
            "id": tx.id,
            "type": tx.tx_type,
            "type_display": tx.get_tx_type_display(),
            "points": tx.points,
            "balance_after": tx.balance_after,
            "purchase_amount": str(tx.purchase_amount) if tx.purchase_amount else None,
            "expire_date": tx.expire_date.isoformat() if tx.expire_date else None,
            "note": tx.note,
            "created_at": tx.created_at.isoformat(),
        }
        for tx in txs
    ]
    return JsonResponse({"ok": True, "transactions": data})

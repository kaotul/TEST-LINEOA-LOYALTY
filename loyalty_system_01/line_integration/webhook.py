import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import FollowEvent, MessageEvent, TextMessageContent

from customers.models import Customer
from line_integration.client import reply_text, _get_api

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def line_webhook(request):
    """
    Endpoint ที่ตั้งไว้ใน LINE Developers Console (Messaging API > Webhook URL)
    จัดการ:
    - FollowEvent: ลูกค้ากดเพิ่มเพื่อน -> สร้าง Customer record + qr_token อัตโนมัติ
    - MessageEvent (ข้อความ 'คะแนน'): ตอบยอดคะแนนแบบเร็ว ๆ ผ่านแชท (เสริมจากปุ่ม Rich Menu)
    """
    signature = request.headers.get("X-Line-Signature", "")
    body = request.body.decode("utf-8")

    parser = WebhookParser(settings.LINE_CHANNEL_SECRET)
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        return HttpResponseBadRequest("Invalid signature")

    for event in events:
        try:
            _handle_event(event)
        except Exception:
            logger.exception("Error handling LINE event: %s", event)

    return HttpResponse("OK")


def _handle_event(event):
    if isinstance(event, FollowEvent):
        _handle_follow(event)
    elif isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
        _handle_text_message(event)


def _handle_follow(event):
    line_user_id = event.source.user_id
    profile = None
    if settings.LINE_CHANNEL_ACCESS_TOKEN:
        api = _get_api()
        profile = api.get_profile(line_user_id)

    Customer.objects.update_or_create(
        line_user_id=line_user_id,
        defaults={
            "display_name": getattr(profile, "display_name", "") or "",
            "picture_url": getattr(profile, "picture_url", "") or "",
            "is_active": True,
        },
    )
    reply_text(event.reply_token, "ยินดีต้อนรับสู่ระบบสะสมคะแนน 🎉\nกดเมนู 'คะแนนของฉัน' ด้านล่างเพื่อดู QR Code และคะแนนสะสมได้ตลอดเวลาครับ/ค่ะ")


def _handle_text_message(event):
    text = event.message.text.strip()
    if text in ("คะแนน", "แต้ม", "point", "points"):
        try:
            customer = Customer.objects.get(line_user_id=event.source.user_id)
            reply_text(event.reply_token, f"คุณมีคะแนนสะสม {customer.current_point_balance} คะแนนครับ/ค่ะ")
        except Customer.DoesNotExist:
            reply_text(event.reply_token, "ไม่พบข้อมูลสมาชิก กรุณาเพิ่มเพื่อนใหม่อีกครั้งครับ/ค่ะ")

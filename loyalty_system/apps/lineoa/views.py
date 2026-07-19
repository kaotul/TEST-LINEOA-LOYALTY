import json
import logging

from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from .services import verify_webhook_signature, push_text_message

logger = logging.getLogger(__name__)


@csrf_exempt
def webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    signature = request.headers.get("X-Line-Signature", "")
    if not verify_webhook_signature(request.body, signature):
        return HttpResponseForbidden("invalid signature")

    body = json.loads(request.body or "{}")
    for event in body.get("events", []):
        _handle_event(event)

    return HttpResponse(status=200)


def _handle_event(event: dict):
    event_type = event.get("type")
    source = event.get("source", {})
    line_user_id = source.get("userId")

    if event_type == "follow" and line_user_id:
        push_text_message(
            line_user_id,
            "ยินดีต้อนรับสู่ระบบสมาชิกสะสมแต้ม! 🎉\n"
            "กดเมนู 'คะแนนของฉัน' ด้านล่างเพื่อดูคะแนนสะสม ประวัติ และ QR Code สำหรับรับแต้มได้เลย",
        )
    # postback / message events อื่นๆ (เช่นปุ่มใน Rich Menu ที่เป็น postback แทนที่จะเป็น URI)
    # สามารถเพิ่ม logic เฉพาะได้ที่นี่

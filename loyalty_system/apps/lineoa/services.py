import base64
import hashlib
import hmac
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

LINE_VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_RICHMENU_URL = "https://api.line.me/v2/bot/richmenu"
LINE_RICHMENU_UPLOAD_URL = "https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content"
LINE_RICHMENU_DEFAULT_URL = "https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}"


def verify_line_id_token(id_token: str):
    """
    Verify LIFF ID Token กับ LINE Login API (server-side)
    คืนค่า claims (sub, name, picture, ...) ถ้า valid, มิฉะนั้นคืน None
    ดูเอกสาร: https://developers.line.biz/en/reference/line-login/#verify-id-token
    """
    try:
        resp = requests.post(
            LINE_VERIFY_URL,
            data={"id_token": id_token, "client_id": settings.LINE_CHANNEL_ID},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("LINE id_token verify failed: %s %s", resp.status_code, resp.text)
            return None
        return resp.json()
    except requests.RequestException:
        logger.exception("Error calling LINE verify endpoint")
        return None


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """ตรวจสอบ X-Line-Signature ของ webhook request ด้วย channel secret"""
    if not signature:
        return False
    mac = hmac.new(settings.LINE_CHANNEL_SECRET.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _headers():
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}",
    }


def push_text_message(line_user_id: str, text: str):
    """ส่งข้อความแจ้งเตือนแบบ text ไปหาลูกค้า 1 คน ผ่าน Messaging API push"""
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        logger.warning("LINE_CHANNEL_ACCESS_TOKEN not configured; skip push")
        return None
    payload = {"to": line_user_id, "messages": [{"type": "text", "text": text}]}
    try:
        resp = requests.post(LINE_PUSH_URL, json=payload, headers=_headers(), timeout=10)
        if resp.status_code != 200:
            logger.warning("LINE push failed: %s %s", resp.status_code, resp.text)
        return resp
    except requests.RequestException:
        logger.exception("Error pushing LINE message")
        return None


def push_flex_message(line_user_id: str, alt_text: str, flex_contents: dict):
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        logger.warning("LINE_CHANNEL_ACCESS_TOKEN not configured; skip push")
        return None
    payload = {
        "to": line_user_id,
        "messages": [{"type": "flex", "altText": alt_text, "contents": flex_contents}],
    }
    try:
        resp = requests.post(LINE_PUSH_URL, json=payload, headers=_headers(), timeout=10)
        if resp.status_code != 200:
            logger.warning("LINE push (flex) failed: %s %s", resp.status_code, resp.text)
        return resp
    except requests.RequestException:
        logger.exception("Error pushing LINE flex message")
        return None


def create_rich_menu(rich_menu_object: dict) -> str | None:
    """สร้าง Rich Menu (ยังไม่ใส่รูป) คืน rich_menu_id"""
    resp = requests.post(LINE_RICHMENU_URL, json=rich_menu_object, headers=_headers(), timeout=10)
    if resp.status_code != 200:
        logger.error("create_rich_menu failed: %s %s", resp.status_code, resp.text)
        return None
    return resp.json().get("richMenuId")


def upload_rich_menu_image(rich_menu_id: str, image_bytes: bytes, content_type="image/png"):
    headers = {
        "Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": content_type,
    }
    url = LINE_RICHMENU_UPLOAD_URL.format(rich_menu_id=rich_menu_id)
    resp = requests.post(url, data=image_bytes, headers=headers, timeout=30)
    return resp.status_code == 200


def set_default_rich_menu(rich_menu_id: str):
    url = LINE_RICHMENU_DEFAULT_URL.format(rich_menu_id=rich_menu_id)
    resp = requests.post(url, headers=_headers(), timeout=10)
    return resp.status_code == 200

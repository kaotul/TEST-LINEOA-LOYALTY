"""
Wrapper รอบ line-bot-sdk v3 สำหรับ:
- Push message แจ้งเตือนตอนได้คะแนน / แต้มใกล้หมดอายุ (กติกาข้อ 4)
- Setup Rich Menu ให้ปุ่ม "ดูคะแนนของฉัน" เปิด LIFF (กติกาข้อ 3)
"""
from django.conf import settings
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexMessage,
    FlexContainer,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)


def _get_api() -> MessagingApi:
    config = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
    return MessagingApi(ApiClient(config))


def send_points_earned_message(*, customer, points_earned: int, batch_expires_at):
    """
    หลังพนักงานกดให้คะแนนสำเร็จ ส่ง Flex Message สรุป:
    - คะแนนที่เพิ่งได้รับ
    - คะแนนรวมปัจจุบัน
    - วันหมดอายุของคะแนนก้อนนี้
    """
    total_balance = customer.current_point_balance
    liff_url = f"{settings.LIFF_BASE_URL}/{settings.LIFF_ID}"

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "🎉 ได้รับคะแนนสะสมแล้ว!", "weight": "bold", "size": "lg", "color": "#1DB446"},
                {"type": "text", "text": f"+{points_earned} คะแนน", "size": "xxl", "weight": "bold"},
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "คะแนนรวมปัจจุบัน", "size": "sm", "color": "#666666"},
                        {"type": "text", "text": f"{total_balance} คะแนน", "size": "sm", "align": "end", "weight": "bold"},
                    ],
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "คะแนนชุดนี้หมดอายุ", "size": "sm", "color": "#666666"},
                        {"type": "text", "text": batch_expires_at.strftime("%d/%m/%Y"), "size": "sm", "align": "end"},
                    ],
                },
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "action": {"type": "uri", "label": "ดูคะแนนของฉัน", "uri": liff_url},
                }
            ],
        },
    }

    _push_flex(customer.line_user_id, alt_text=f"ได้รับ {points_earned} คะแนน! คะแนนรวม {total_balance}", bubble=bubble)


def send_expiry_warning_message(*, customer, expiring_points: int, expires_at):
    """แจ้งเตือนล่วงหน้าว่ามีคะแนนกำลังจะหมดอายุ (กติกาข้อ 4)"""
    liff_url = f"{settings.LIFF_BASE_URL}/{settings.LIFF_ID}"
    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "⏰ คะแนนใกล้หมดอายุ", "weight": "bold", "size": "lg", "color": "#FF6B6B"},
                {"type": "text", "text": f"{expiring_points} คะแนน", "size": "xxl", "weight": "bold"},
                {"type": "text", "text": f"จะหมดอายุวันที่ {expires_at.strftime('%d/%m/%Y')}", "size": "sm", "color": "#666666", "wrap": True},
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#FF6B6B",
                    "action": {"type": "uri", "label": "ใช้คะแนนตอนนี้", "uri": liff_url},
                }
            ],
        },
    }
    _push_flex(customer.line_user_id, alt_text=f"คะแนน {expiring_points} แต้มใกล้หมดอายุ", bubble=bubble)


def _push_flex(to_user_id: str, *, alt_text: str, bubble: dict):
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        # โหมด dev/test ที่ยังไม่ผูก LINE credential จริง - ไม่ throw error ให้ระบบอื่นทำงานต่อได้
        return
    api = _get_api()
    message = FlexMessage(alt_text=alt_text, contents=FlexContainer.from_dict(bubble))
    api.push_message(PushMessageRequest(to=to_user_id, messages=[message]))


def reply_text(reply_token: str, text: str):
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        return
    from linebot.v3.messaging import ReplyMessageRequest

    api = _get_api()
    api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=text)]))

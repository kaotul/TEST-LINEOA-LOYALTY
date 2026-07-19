"""
Thin client around two LINE HTTP APIs:

1. `verify_id_token`   -- LINE Login "verify" endpoint. This is the ONLY
   place we decide who a request is from. The LIFF frontend sends the raw
   ID token it got from `liff.getIDToken()`; we hand it to LINE and LINE
   hands back the verified `sub` (the user's LINE user id), `name` and
   `picture`. We never trust a user id sent directly in a request body,
   because that would let anyone register as anyone else.

2. `push_member_card`  -- LINE Messaging API "push" endpoint, used to send
   the Flex Message member card into the user's chat with the OA right
   after registration succeeds. Optional: skipped if no channel access
   token is configured.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"
PUSH_URL = "https://api.line.me/v2/bot/message/push"
REQUEST_TIMEOUT = 5  # seconds


class LineTokenError(Exception):
    """Raised when an ID token is missing, expired, malformed, or for the wrong channel."""


def verify_id_token(id_token: str) -> dict:
    """
    Verify a LIFF ID token with LINE and return its claims.

    Returns a dict with at least: sub, name, picture, aud, exp.
    Raises LineTokenError on any failure -- callers should turn that into
    a 401 response rather than proceeding.
    """
    if not id_token:
        raise LineTokenError("Missing ID token.")

    try:
        resp = requests.post(
            VERIFY_URL,
            data={"id_token": id_token, "client_id": settings.LINE_LOGIN_CHANNEL_ID},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning("LINE verify request failed: %s", exc)
        raise LineTokenError("Could not reach LINE to verify the token.") from exc

    if resp.status_code != 200:
        logger.info("LINE rejected ID token: %s %s", resp.status_code, resp.text)
        raise LineTokenError("Invalid or expired LINE session. Please reopen the app.")

    claims = resp.json()

    # Belt-and-braces: verify() already checks aud/exp server-side on LINE's
    # end, but we re-check the channel id locally in case of misconfiguration.
    if claims.get("aud") != settings.LINE_LOGIN_CHANNEL_ID:
        raise LineTokenError("Token was issued for a different LINE Login channel.")

    if not claims.get("sub"):
        raise LineTokenError("Token did not contain a user id.")

    return claims


def build_member_card_flex(member) -> dict:
    """Build the Flex Message 'bubble' JSON representing a member's card."""
    picture = member.picture_url or "https://via.placeholder.com/300x300.png?text=Member"
    return {
        "type": "bubble",
        "size": "mega",
        "hero": {
            "type": "image",
            "url": picture,
            "size": "full",
            "aspectRatio": "20:9",
            "aspectMode": "cover",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "backgroundColor": "#0E2A2E",
            "paddingAll": "20px",
            "contents": [
                {
                    "type": "text",
                    "text": "MEMBER CARD",
                    "size": "xs",
                    "color": "#D4A24C",
                    "weight": "bold",
                    "letterSpacing": "2px",
                },
                {
                    "type": "text",
                    "text": f"{member.first_name} {member.last_name}",
                    "size": "xl",
                    "color": "#FFFFFF",
                    "weight": "bold",
                    "margin": "sm",
                },
                {
                    "type": "text",
                    "text": member.member_no,
                    "size": "md",
                    "color": "#9FC7C2",
                    "margin": "md",
                },
                {"type": "separator", "margin": "lg", "color": "#1F4448"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "lg",
                    "spacing": "xs",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"Joined {member.created_at.strftime('%d %b %Y')}",
                            "size": "xs",
                            "color": "#7FA8A3",
                        },
                    ],
                },
            ],
        },
        "styles": {"footer": {"separator": True}},
    }


def push_member_card(user_id: str, member) -> None:
    """Push the Flex Message member card to the user. No-op if unconfigured."""
    if not settings.LINE_CHANNEL_ACCESS_TOKEN:
        logger.info("LINE_CHANNEL_ACCESS_TOKEN not set; skipping member card push.")
        return

    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "flex",
                "altText": f"Welcome, {member.first_name}! Here is your member card.",
                "contents": build_member_card_flex(member),
            }
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(PUSH_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            logger.warning("LINE push failed: %s %s", resp.status_code, resp.text)
    except requests.RequestException as exc:
        # Registration must still succeed even if the push fails -- log and move on.
        logger.warning("LINE push request error: %s", exc)

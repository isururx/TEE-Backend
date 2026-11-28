import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TEXTLK_API_URL = "https://app.text.lk/api/http/sms/send"


def format_phone_number(phone_number: str) -> str:
    """Normalize common Sri Lankan phone formats to 94XXXXXXXXX."""
    if not phone_number:
        raise ValueError("No phone number is configured for this account")

    value = "".join(ch for ch in str(phone_number).strip() if ch.isdigit() or ch == "+")
    if value.startswith("+94"):
        normalized = value[1:]
    elif value.startswith("94"):
        normalized = value
    elif value.startswith("0"):
        normalized = "94" + value[1:]
    elif len(value) == 9 and value.startswith("7"):
        # Worker.phone_num is a legacy BIGINT column; it may have lost the leading zero.
        normalized = "94" + value
    else:
        raise ValueError("Phone number must be a Sri Lankan number starting with 0 or +94")

    digits = normalized[2:]
    if len(digits) != 9 or not digits.isdigit():
        raise ValueError("Invalid Sri Lankan phone number")
    return normalized


async def send_sms(recipient: str, message: str) -> dict:
    """Send an SMS through the configured Text.lk account."""
    api_token = os.getenv("TEXTLK_API_TOKEN")
    sender_id = os.getenv("TEXTLK_SENDER_ID")
    if not api_token or not api_token.strip():
        raise RuntimeError("TEXTLK_API_TOKEN is not configured")
    if not sender_id or not sender_id.strip():
        raise RuntimeError("TEXTLK_SENDER_ID is not configured")

    payload = {
        "api_token": api_token.strip(),
        "recipient": format_phone_number(recipient),
        "sender_id": sender_id.strip(),
        "type": "plain",
        "message": message,
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(TEXTLK_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            response_data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"Text.lk SMS request failed: {type(exc).__name__}") from exc

    if not isinstance(response_data, dict) or response_data.get("status") != "success":
        provider_message = response_data.get("message") if isinstance(response_data, dict) else None
        raise RuntimeError(provider_message or "Text.lk SMS sending failed")
    return response_data

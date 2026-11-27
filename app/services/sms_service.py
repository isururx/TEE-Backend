import os
import httpx
from dotenv import load_dotenv

load_dotenv()


TEXTLK_API_URL = "https://app.text.lk/api/http/sms/send"

TEXTLK_API_TOKEN = os.getenv("TEXTLK_API_TOKEN")
TEXTLK_SENDER_ID = os.getenv("TEXTLK_SENDER_ID")


def format_phone_number(phone_number: str) -> str:
    """
    Convert Sri Lankan phone numbers to international format.

    0771234567 -> 94771234567
    +94771234567 -> 94771234567
    94771234567 -> 94771234567
    """

    phone_number = phone_number.strip()

    if phone_number.startswith("+94"):
        return phone_number[1:]

    if phone_number.startswith("94"):
        return phone_number

    if phone_number.startswith("0"):
        return "94" + phone_number[1:]

    raise ValueError("Invalid Sri Lankan phone number")


async def send_sms(
    recipient: str,
    message: str
):
    recipient = format_phone_number(recipient)

    payload = {
        "api_token": TEXTLK_API_TOKEN,
        "recipient": recipient,
        "sender_id": TEXTLK_SENDER_ID,
        "type": "plain",
        "message": message
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:

        response = await client.post(
            TEXTLK_API_URL,
            json=payload,
            headers=headers
        )

    response_data = response.json()

    if response_data.get("status") != "success":
        raise Exception(
            response_data.get(
                "message",
                "Text.lk SMS sending failed"
            )
        )

    return response_data
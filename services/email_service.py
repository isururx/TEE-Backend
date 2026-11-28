import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from dotenv import load_dotenv

load_dotenv()


def _required_setting(name: str, value: str | None) -> str:
    if not value or not value.strip():
        raise RuntimeError(f"{name} is not configured")
    return value.strip()


def send_otp_email(recipient_email: str, otp: str, purpose: str = "2FA") -> None:
    """Send an OTP using SMTP. Supports STARTTLS (587) and implicit TLS (465)."""
    recipient_email = _required_setting("recipient email", recipient_email)
    if "\r" in recipient_email or "\n" in recipient_email:
        raise ValueError("Invalid recipient email address")

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError as exc:
        raise RuntimeError("SMTP_PORT must be a valid port number") from exc
    if not 1 <= smtp_port <= 65535:
        raise RuntimeError("SMTP_PORT must be between 1 and 65535")

    smtp_user = _required_setting("SMTP_USER", os.getenv("SMTP_USER"))
    smtp_password = _required_setting("SMTP_PASSWORD", os.getenv("SMTP_PASSWORD"))
    from_email = (os.getenv("SMTP_FROM_EMAIL") or smtp_user).strip()
    from_name = os.getenv("SMTP_FROM_NAME", "TEE Estate System").strip()

    if purpose.lower() == "password reset":
        subject = "TEE Estate System - Password Reset Code"
        intro = "Use this code to reset your TEE Estate System password:"
    else:
        subject = "TEE Estate System - Your 2FA Verification Code"
        intro = "Your TEE Estate System verification code is:"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = recipient_email
    msg.set_content(
        f"{intro} {otp}\n\n"
        "This code will expire in 5 minutes.\n"
        "If you did not request this code, please ignore this email."
    )

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

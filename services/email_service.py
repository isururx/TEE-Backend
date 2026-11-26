import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def send_otp_email(recipient_email: str, otp: str) -> None:
    """Send a 6-digit 2FA OTP verification email via SMTP STARTTLS."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_name = os.getenv("SMTP_FROM_NAME", "TEE Estate System")
    from_email = os.getenv("SMTP_FROM_EMAIL") or smtp_user

    if not smtp_user or not smtp_password:
        raise RuntimeError("SMTP credentials are not configured")

    msg = EmailMessage()
    msg["Subject"] = "TEE Estate System - Your 2FA Verification Code"
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = recipient_email
    msg.set_content(
        f"Your TEE Estate System verification code is: {otp}\n\n"
        "This code will expire in 5 minutes.\n"
        "If you did not request this code, please ignore this email."
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)

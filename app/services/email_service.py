import os
import smtplib
import ssl
from email.message import EmailMessage
from html import escape
from pathlib import Path
from dotenv import load_dotenv

# Resolve .env from the backend project root, not the process working directory.
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=False)


def _smtp_settings() -> tuple[str, int, str, str, str, str]:
    """Load and validate SMTP settings without exposing credentials."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError as exc:
        raise RuntimeError("SMTP_PORT must be a valid port number (587 or 465)") from exc

    username = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_name = os.getenv("SMTP_FROM_NAME", "TEE Estate System").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", "").strip() or username

    if not host:
        raise RuntimeError("SMTP_HOST is not configured")
    if port not in (465, 587):
        raise RuntimeError("SMTP_PORT must be 587 (STARTTLS) or 465 (SSL)")
    if not username or not password:
        raise RuntimeError("SMTP_USER and SMTP_PASSWORD must be configured in the backend .env file")
    if not from_email or "@" not in from_email:
        raise RuntimeError("SMTP_FROM_EMAIL must be a valid sender email address")
    if "\r" in from_name or "\n" in from_name:
        raise RuntimeError("SMTP_FROM_NAME contains invalid header characters")

    return host, port, username, password, from_name, from_email


def _send_branded_otp_email(
    recipient_email: str,
    otp: str,
    subject: str,
    heading: str,
    instruction: str,
) -> None:
    """Send a branded OTP email using authenticated SMTP with TLS."""
    if not recipient_email or "@" not in recipient_email:
        raise ValueError("A valid recipient email address is required")
    if len(str(otp)) != 6 or not str(otp).isdigit():
        raise ValueError("OTP must contain exactly six digits")

    host, port, username, password, from_name, from_email = _smtp_settings()
    safe_otp = escape(str(otp))
    safe_heading = escape(heading)
    safe_instruction = escape(instruction)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = recipient_email
    msg.set_content(
        f"TEE Estate System\n{heading}\n\n{instruction}\n\n"
        f"Your 6-digit verification code is: {otp}\n\n"
        "This code will expire in 5 minutes. If you did not request it, "
        "please ignore this email or contact your system administrator."
    )
    msg.add_alternative(
        f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{safe_heading}</title></head>
<body style="margin:0;padding:24px;background:#f3f5f4;font-family:Arial,Helvetica,sans-serif;color:#4b5563;">
  <main style="max-width:600px;margin:auto;background:#fff;border:1px solid #e5e7eb;border-radius:16px;overflow:hidden;">
    <header style="background:#194d3a;padding:32px 20px;text-align:center;color:#fff;">
      <div style="font-size:28px;font-weight:700;">TEE Estate System</div>
      <div style="margin-top:8px;color:#c4e2d2;">AI-Powered Tea Estate Management</div>
    </header>
    <section style="padding:36px 28px;">
      <h2 style="color:#214d3b;">{safe_heading}</h2>
      <p>Hello,</p><p>{safe_instruction}</p>
      <div style="margin:28px 0;padding:26px 12px;background:#edf7f0;border:2px dashed #42bd83;border-radius:12px;text-align:center;">
        <span style="font-size:36px;font-weight:700;letter-spacing:10px;color:#204d3c;">{safe_otp}</span>
      </div>
      <p style="text-align:center;color:#d62839;">This code expires in 5 minutes.</p>
      <hr style="border:0;border-top:1px solid #e5e7eb;margin:28px 0;">
      <p style="font-size:13px;color:#737d88;">If you did not request this code, please ignore this email or contact your tea estate system administrator.</p>
    </section>
  </main>
</body>
</html>""",
        subtype="html",
    )

    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20, context=context) as server:
            server.ehlo()
            server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            server.send_message(msg)


def send_otp_email(recipient_email: str, otp: str) -> None:
    """Send the login two-factor authentication code."""
    _send_branded_otp_email(
        recipient_email, otp,
        "TEE Estate System - Your 2FA Verification Code",
        "Two-Factor Authentication",
        "Use the following 6-digit code to complete your login.",
    )


def send_password_reset_otp_email(recipient_email: str, otp: str) -> None:
    """Send the password-reset verification code."""
    _send_branded_otp_email(
        recipient_email, otp,
        "TEE Estate System - Password Reset Verification Code",
        "Password Reset Verification",
        "Use the following 6-digit code to continue resetting your password.",
    )

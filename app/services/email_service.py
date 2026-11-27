import os
import smtplib
from email.message import EmailMessage
from html import escape
from dotenv import load_dotenv

load_dotenv()


def _send_branded_otp_email(
    recipient_email: str,
    otp: str,
    subject: str,
    heading: str,
    instruction: str,
) -> None:
    """Send a branded TEE OTP email with HTML and plain-text alternatives."""
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_name = os.getenv("SMTP_FROM_NAME", "TEE Estate System")
    from_email = os.getenv("SMTP_FROM_EMAIL") or smtp_user

    if not smtp_user or not smtp_password:
        raise RuntimeError("SMTP credentials are not configured")

    safe_otp = escape(str(otp))
    safe_heading = escape(heading)
    safe_instruction = escape(instruction)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = recipient_email

    msg.set_content(
        f"TEE Estate System\n"
        f"{heading}\n\n"
        f"{instruction}\n\n"
        f"Your 6-digit verification code is: {otp}\n\n"
        "This code will expire in 5 minutes.\n"
        "If you did not request this code, please ignore this email or contact your tea estate system administrator."
    )

    msg.add_alternative(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_heading}</title>
</head>
<body style="margin:0;padding:0;background-color:#f3f5f4;font-family:Arial,Helvetica,sans-serif;color:#4b5563;">
  <div style="max-width:650px;margin:24px auto;background:#ffffff;border:1px solid #e5e7eb;">
    <div style="background:linear-gradient(110deg,#194d3a,#28684f);padding:42px 24px;text-align:center;color:#ffffff;border-radius:20px 20px 0 0;">
      <div style="font-size:30px;font-weight:700;line-height:1.3;">🌱 TEE Estate System</div>
      <div style="margin-top:12px;font-size:15px;color:#c4e2d2;">AI-Powered Tea Estate Management</div>
    </div>
    <div style="padding:48px 40px 44px;">
      <h2 style="margin:0 0 20px;color:#214d3b;font-size:22px;font-weight:600;">{safe_heading}</h2>
      <p style="margin:0 0 8px;font-size:16px;line-height:1.6;">Hello,</p>
      <p style="margin:0;font-size:16px;line-height:1.6;">{safe_instruction}</p>
      <div style="margin:30px 0;padding:32px 16px;background:#edf7f0;border:2px dashed #42bd83;border-radius:16px;text-align:center;">
        <div style="font-size:38px;line-height:1.3;font-weight:700;letter-spacing:12px;color:#204d3c;">{safe_otp}</div>
      </div>
      <p style="margin:0 0 26px;text-align:center;color:#ef233c;font-size:15px;line-height:1.5;">⌛ This code will expire in 5 minutes.</p>
      <div style="border-top:1px solid #e5e7eb;padding-top:26px;font-size:14px;line-height:1.6;color:#737d88;">
        If you did not request this verification code, please ignore this email or contact your tea estate system administrator immediately.
      </div>
    </div>
  </div>
</body>
</html>""",
        subtype="html",
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


def send_otp_email(recipient_email: str, otp: str) -> None:
    """Send the existing 2FA OTP using the branded TEE email layout."""
    _send_branded_otp_email(
        recipient_email=recipient_email,
        otp=otp,
        subject="TEE Estate System - Your 2FA Verification Code",
        heading="Two-Factor Authentication (MFA)",
        instruction="Please use the following 6-digit verification code to complete your login.",
    )


def send_password_reset_otp_email(recipient_email: str, otp: str) -> None:
    """Send a password-reset OTP using the same branded TEE email layout."""
    _send_branded_otp_email(
        recipient_email=recipient_email,
        otp=otp,
        subject="TEE Estate System - Password Reset Verification Code",
        heading="Password Reset Verification",
        instruction="We received a request to reset your TEE Estate System password. Please use the following 6-digit verification code to continue.",
    )

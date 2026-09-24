import os
import smtplib
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "TEE Estate System")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)


def _is_dummy_config() -> bool:
    """Check if SMTP credentials are still default placeholders."""
    if not SMTP_USER or not SMTP_PASSWORD:
        return True
    if "your_email@gmail.com" in SMTP_USER.lower() or "your_16_digit" in SMTP_PASSWORD.lower():
        return True
    return False


def _build_html_email(otp: str, recipient_name: str) -> str:
    """Create a styled HTML email template."""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>TEE Verification Code</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f7f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
      <table border="0" cellpadding="0" cellspacing="0" width="100%" style="table-layout: fixed;">
        <tr>
          <td align="center" style="padding: 40px 15px;">
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 520px; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.06);">
              <!-- Header -->
              <tr>
                <td style="background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 100%); padding: 32px 24px; text-align: center;">
                  <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: 0.5px;">🌱 TEE Estate System</h1>
                  <p style="margin: 6px 0 0 0; color: #b7e4c7; font-size: 13px;">AI-Powered Tea Estate Management</p>
                </td>
              </tr>
              <!-- Content -->
              <tr>
                <td style="padding: 36px 32px;">
                  <h2 style="margin: 0 0 12px 0; color: #1b4332; font-size: 18px; font-weight: 600;">Two-Factor Authentication (MFA)</h2>
                  <p style="margin: 0 0 24px 0; color: #495057; font-size: 14px; line-height: 1.6;">
                    Hello <strong>{recipient_name}</strong>,<br>
                    Please use the following 6-digit verification code to complete your login.
                  </p>
                  
                  <!-- OTP Card -->
                  <div style="background-color: #edf7f0; border: 2px dashed #52b788; border-radius: 12px; padding: 20px; text-align: center; margin: 24px 0;">
                    <span style="font-size: 34px; font-weight: 800; letter-spacing: 8px; color: #1b4332; font-family: monospace;">{otp}</span>
                  </div>

                  <p style="margin: 0 0 8px 0; color: #d90429; font-size: 13px; font-weight: 600; text-align: center;">
                    ⏳ This code will expire in 5 minutes.
                  </p>
                  <p style="margin: 20px 0 0 0; color: #6c757d; font-size: 12px; line-height: 1.5; border-top: 1px solid #e9ecef; padding-top: 20px;">
                    If you did not request this verification code, please ignore this email or contact your tea estate system administrator immediately.
                  </p>
                </td>
              </tr>
              <!-- Footer -->
              <tr>
                <td style="background-color: #f8f9fa; padding: 18px 24px; text-align: center; border-top: 1px solid #eeeeee;">
                  <p style="margin: 0; color: #adb5bd; font-size: 11px;">
                    &copy; 2026 TEE - Tea Estate Management & AI Disease Detection System.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


def _send_smtp_sync(recipient_email: str, otp: str, recipient_name: str) -> bool:
    """Synchronous worker that performs TLS connection and sends email via SMTP."""
    if _is_dummy_config():
        print("[Email Service] SMTP is using placeholder credentials in .env.")
        print(f"[Email Service] Simulated OTP Email sent to {recipient_email} | OTP: {otp}")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your TEE Verification Code: {otp}"
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = recipient_email

    # Plain-text alternative
    plain_text = (
        f"Hello {recipient_name},\n\n"
        f"Your TEE verification code is: {otp}\n\n"
        "This code will expire in 5 minutes.\n"
        "If you did not request this code, please ignore this message."
    )
    msg.attach(MIMEText(plain_text, "plain"))

    # HTML alternative
    html_text = _build_html_email(otp, recipient_name)
    msg.attach(MIMEText(html_text, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            print(f"[Email Service] OTP successfully sent to {recipient_email}")
            return True
    except Exception as e:
        print(f"[Email Service] Error sending email to {recipient_email}: {repr(e)}")
        # Even if sending fails over network, log the OTP in server console for local testing
        print(f"[Email Service Fallback] Terminal OTP: {otp}")
        return False


async def send_otp_email(recipient_email: str, otp: str, recipient_name: str = "User") -> bool:
    """
    Async non-blocking function to send OTP email via SMTP thread pool.
    """
    if not recipient_email or "@" not in recipient_email:
        print(f"[Email Service] Invalid email address: {recipient_email}")
        return False

    return await asyncio.to_thread(_send_smtp_sync, recipient_email, otp, recipient_name)


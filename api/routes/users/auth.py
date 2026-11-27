from datetime import datetime, timedelta
from secrets import randbelow, token_urlsafe

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.password import hash_password, needs_rehash, verify_password
from app.core.security import create_access_token
from app.db.database import get_db
from app.db.models.user import User
from app.db.models.worker import Worker
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    VerifyResetOtpRequest,
)
from app.services.email_service import send_otp_email


router = APIRouter()

# Temporary in-memory stores. For multi-instance deployments, move these to Redis.
otp_store = {}
reset_otp_store = {}
password_reset_tokens = {}

RESET_OTP_EXPIRY_MINUTES = 5
RESET_TOKEN_EXPIRY_MINUTES = 10
RESET_OTP_MAX_ATTEMPTS = 5
RESET_OTP_RESEND_SECONDS = 60


class Verify2FARequest(BaseModel):
    user_id: int
    otp: str


class ResendOtpRequest(BaseModel):
    user_id: int
    method: str = "email"


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "user***@gmail.com"
    local, domain = email.split("@", 1)
    prefix = local[:3] if len(local) >= 3 else local[:1]
    return f"{prefix}***@{domain}"


def _mask_phone(phone: str) -> str:
    if not phone:
        return "Not set"
    cleaned = phone.strip()
    if len(cleaned) <= 4:
        return cleaned
    return f"{cleaned[:3]} *** {cleaned[-4:]}"


def _send_otp_email_bg(recipient_email: str, otp: str, purpose: str = "2FA") -> None:
    try:
        send_otp_email(recipient_email=recipient_email, otp=otp, purpose=purpose)
    except Exception as exc:
        # Do not log OTP values or SMTP credentials.
        print("Background email sending error:", type(exc).__name__)


@router.post("/verify-2fa")
async def verify_2fa(data: Verify2FARequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stored_otp = otp_store.get(user.id)
    if not stored_otp:
        raise HTTPException(status_code=401, detail="No active verification code")

    if datetime.utcnow() > stored_otp["expires_at"]:
        otp_store.pop(user.id, None)
        raise HTTPException(status_code=401, detail="Verification code has expired")

    if data.otp != stored_otp["otp"]:
        raise HTTPException(status_code=401, detail="Invalid verification code")

    otp_store.pop(user.id, None)
    access_token = create_access_token(user_id=user.id, role=user.role)

    return {
        "success": True,
        "message": "2FA verification successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    }


@router.post("/login")
async def login(
    data: LoginRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.name == data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    if not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Upgrade legacy plain-text passwords (and outdated Argon2 hashes) on successful login.
    if needs_rehash(user.password):
        upgraded_hash = hash_password(data.password)
        user.password = upgraded_hash
        worker = db.query(Worker).filter(Worker.id == user.id).first()
        if worker:
            worker.password = upgraded_hash
        db.commit()

    otp = f"{randbelow(1000000):06d}"
    otp_store[user.id] = {
        "otp": otp,
        "expires_at": datetime.utcnow() + timedelta(minutes=5),
    }

    if user.email:
        background_tasks.add_task(_send_otp_email_bg, user.email, otp, "2FA")

    return {
        "success": True,
        "message": "Verification code sent",
        "requires_2fa": True,
        "user_id": user.id,
        "masked_email": _mask_email(user.email),
        "masked_phone": _mask_phone(user.phone_num),
    }


@router.post("/resend-otp")
async def resend_otp(
    data: ResendOtpRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    method = (data.method or "email").lower()
    if method != "email":
        raise HTTPException(status_code=400, detail="Only email OTP is currently supported")
    if not user.email:
        raise HTTPException(status_code=400, detail="User email is not configured")

    otp = f"{randbelow(1000000):06d}"
    otp_store[user.id] = {
        "otp": otp,
        "expires_at": datetime.utcnow() + timedelta(minutes=5),
    }
    background_tasks.add_task(_send_otp_email_bg, user.email, otp, "2FA")

    return {"success": True, "message": "Verification code sent via email", "method": "email"}


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email = data.email.strip().lower()
    user = db.query(User).filter(User.email.ilike(email)).first()

    # Keep the response identical whether the email exists or not.
    generic_response = {
        "success": True,
        "message": "If the email is registered, a password reset code will be sent.",
    }
    if not user:
        return generic_response

    now = datetime.utcnow()
    previous = reset_otp_store.get(email)
    if previous and (now - previous["created_at"]).total_seconds() < RESET_OTP_RESEND_SECONDS:
        return generic_response

    otp = f"{randbelow(1000000):06d}"
    reset_otp_store[email] = {
        "user_id": user.id,
        "otp": otp,
        "created_at": now,
        "expires_at": now + timedelta(minutes=RESET_OTP_EXPIRY_MINUTES),
        "attempts": 0,
    }
    background_tasks.add_task(_send_otp_email_bg, user.email, otp, "password reset")
    return generic_response


@router.post("/verify-reset-otp")
async def verify_reset_otp(data: VerifyResetOtpRequest):
    email = data.email.strip().lower()
    stored = reset_otp_store.get(email)

    if not stored or datetime.utcnow() > stored["expires_at"]:
        reset_otp_store.pop(email, None)
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    stored["attempts"] += 1
    if stored["attempts"] > RESET_OTP_MAX_ATTEMPTS:
        reset_otp_store.pop(email, None)
        raise HTTPException(status_code=429, detail="Too many incorrect attempts")

    if data.otp != stored["otp"]:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    reset_otp_store.pop(email, None)
    reset_token = token_urlsafe(32)
    password_reset_tokens[reset_token] = {
        "user_id": stored["user_id"],
        "expires_at": datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES),
    }
    return {
        "success": True,
        "message": "Reset code verified",
        "reset_token": reset_token,
        "expires_in_minutes": RESET_TOKEN_EXPIRY_MINUTES,
    }


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    reset_data = password_reset_tokens.get(data.reset_token)
    if not reset_data or datetime.utcnow() > reset_data["expires_at"]:
        password_reset_tokens.pop(data.reset_token, None)
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token")

    user = db.query(User).filter(User.id == reset_data["user_id"]).first()
    if not user:
        password_reset_tokens.pop(data.reset_token, None)
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token")

    new_hash = hash_password(data.new_password)
    user.password = new_hash
    worker = db.query(Worker).filter(Worker.id == user.id).first()
    if worker:
        worker.password = new_hash

    db.commit()
    password_reset_tokens.pop(data.reset_token, None)
    return {"success": True, "message": "Password reset successful"}

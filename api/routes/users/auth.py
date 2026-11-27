from datetime import datetime, timedelta
from secrets import randbelow, token_urlsafe
from threading import Lock

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
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
from app.api.dependencies.auth import get_current_user

router = APIRouter()

# Login challenges are short-lived. For multi-worker production deployments,
# move this store to Redis (the API contract is already challenge-ID based).
_login_challenges: dict[str, dict] = {}
_challenge_lock = Lock()

RESET_OTP_EXPIRY_MINUTES = 5
RESET_TOKEN_EXPIRY_MINUTES = 10
RESET_OTP_MAX_ATTEMPTS = 5
RESET_OTP_RESEND_SECONDS = 60

# Existing password-reset flow retained for compatibility. It should also be
# moved to persistent storage before horizontal scaling.
reset_otp_store = {}
password_reset_tokens = {}


class Verify2FARequest(BaseModel):
    challenge_id: str = Field(min_length=20, max_length=128)
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\\d{6}$")


class ResendOtpRequest(BaseModel):
    challenge_id: str = Field(min_length=20, max_length=128)
    method: str = "email"


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "your registered email"
    local, domain = email.split("@", 1)
    prefix = local[:2] if len(local) > 2 else local[:1]
    return f"{prefix}***@{domain}"


def _mask_phone(phone: str | None) -> str:
    if not phone:
        return "Not set"
    cleaned = phone.strip()
    return f"{cleaned[:3]} *** {cleaned[-4:]}" if len(cleaned) > 4 else cleaned


def _send_otp_email_bg(recipient_email: str, otp: str, purpose: str = "2FA") -> None:
    try:
        send_otp_email(recipient_email=recipient_email, otp=otp, purpose=purpose)
    except Exception as exc:
        # Never log OTP values or SMTP credentials.
        print("Background email sending error:", type(exc).__name__)


def _issue_login_challenge(user: User, background_tasks: BackgroundTasks) -> dict:
    if not user.email:
        raise HTTPException(status_code=400, detail="No email address is configured for this account")

    challenge_id = token_urlsafe(32)
    otp = f"{randbelow(1_000_000):06d}"
    now = datetime.utcnow()
    with _challenge_lock:
        _login_challenges[challenge_id] = {
            "user_id": user.id,
            "otp": otp,
            "created_at": now,
            "expires_at": now + timedelta(minutes=5),
            "attempts": 0,
            "last_sent_at": now,
        }
    background_tasks.add_task(_send_otp_email_bg, user.email, otp, "2FA")
    return {
        "success": True,
        "requires_2fa": True,
        "challenge_id": challenge_id,
        "masked_email": _mask_email(user.email),
        "expires_in_seconds": 300,
    }


@router.post("/login")
async def login(
    data: LoginRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    username = data.username.strip()
    user = db.query(User).filter(User.name == username).first()
    if not user or not verify_password(data.password, user.password):
        # Same response for unknown username and incorrect password.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    if needs_rehash(user.password):
        upgraded_hash = hash_password(data.password)
        user.password = upgraded_hash
        worker = db.query(Worker).filter(Worker.id == user.id).first()
        if worker:
            worker.password = upgraded_hash
        db.commit()

    return _issue_login_challenge(user, background_tasks)


@router.post("/verify-2fa")
async def verify_2fa(data: Verify2FARequest, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    with _challenge_lock:
        challenge = _login_challenges.get(data.challenge_id)
        if not challenge:
            raise HTTPException(status_code=401, detail="Verification challenge is invalid or expired")
        if now > challenge["expires_at"]:
            _login_challenges.pop(data.challenge_id, None)
            raise HTTPException(status_code=401, detail="Verification code has expired")
        challenge["attempts"] += 1
        if challenge["attempts"] > 5:
            _login_challenges.pop(data.challenge_id, None)
            raise HTTPException(status_code=429, detail="Too many incorrect attempts. Please log in again.")
        if not __import__("hmac").compare_digest(data.otp, challenge["otp"]):
            raise HTTPException(status_code=401, detail="Invalid verification code")
        user_id = challenge["user_id"]
        _login_challenges.pop(data.challenge_id, None)

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="User account is unavailable")

    return {
        "success": True,
        "message": "Verification successful",
        "access_token": create_access_token(user_id=user.id, role=user.role),
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {
            "id": user.id,
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }


@router.post("/resend-otp")
async def resend_otp(
    data: ResendOtpRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if data.method.lower() != "email":
        raise HTTPException(status_code=400, detail="Only email OTP is currently supported")

    now = datetime.utcnow()
    with _challenge_lock:
        challenge = _login_challenges.get(data.challenge_id)
        if not challenge or now > challenge["expires_at"]:
            _login_challenges.pop(data.challenge_id, None)
            raise HTTPException(status_code=401, detail="Verification challenge is invalid or expired")
        if (now - challenge["last_sent_at"]).total_seconds() < 60:
            raise HTTPException(status_code=429, detail="Please wait before requesting another code")
        user_id = challenge["user_id"]

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active or not user.email:
        raise HTTPException(status_code=403, detail="User account is unavailable")

    otp = f"{randbelow(1_000_000):06d}"
    with _challenge_lock:
        # Challenge may have expired while the user record was being loaded.
        challenge = _login_challenges.get(data.challenge_id)
        if not challenge:
            raise HTTPException(status_code=401, detail="Verification challenge is invalid or expired")
        challenge.update({
            "otp": otp,
            "attempts": 0,
            "created_at": now,
            "expires_at": now + timedelta(minutes=5),
            "last_sent_at": now,
        })
    background_tasks.add_task(_send_otp_email_bg, user.email, otp, "2FA")
    return {"success": True, "message": "Verification code sent", "expires_in_seconds": 300}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "user_id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
    }


@router.post("/logout")
async def logout():
    # Access tokens are stateless and remain valid until their 60-minute expiry.
    # The frontend clears its local session immediately.
    return {"success": True, "message": "Logged out"}


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email = data.email.strip().lower()
    user = db.query(User).filter(User.email.ilike(email)).first()
    response = {"success": True, "message": "If the email is registered, a password reset code will be sent."}
    if not user:
        return response

    now = datetime.utcnow()
    previous = reset_otp_store.get(email)
    if previous and (now - previous["created_at"]).total_seconds() < RESET_OTP_RESEND_SECONDS:
        return response

    otp = f"{randbelow(1_000_000):06d}"
    reset_otp_store[email] = {
        "user_id": user.id,
        "otp": otp,
        "created_at": now,
        "expires_at": now + timedelta(minutes=RESET_OTP_EXPIRY_MINUTES),
        "attempts": 0,
    }
    background_tasks.add_task(_send_otp_email_bg, user.email, otp, "password reset")
    return response


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
    if not __import__("hmac").compare_digest(data.otp, stored["otp"]):
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    reset_otp_store.pop(email, None)
    reset_token = token_urlsafe(32)
    password_reset_tokens[reset_token] = {
        "user_id": stored["user_id"],
        "expires_at": datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES),
    }
    return {"success": True, "message": "Reset code verified", "reset_token": reset_token,
            "expires_in_minutes": RESET_TOKEN_EXPIRY_MINUTES}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
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

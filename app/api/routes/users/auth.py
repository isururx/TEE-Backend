from datetime import datetime, timedelta, timezone
from secrets import randbelow, token_urlsafe
from hashlib import sha256
from hmac import compare_digest, new as hmac_new

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.dependencies.auth import get_current_user
from app.core.security import _require_secret, create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.models.auth_challenge import AuthChallenge
from app.db.models.user import User
from app.schemas.auth import LoginRequest
from app.services.email_service import send_otp_email, send_password_reset_otp_email

router = APIRouter()
OTP_TTL = timedelta(minutes=5)
RESET_TOKEN_TTL = timedelta(minutes=10)
MAX_OTP_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)

class Verify2FARequest(BaseModel):
    user_id: int
    otp: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')

class ResendOtpRequest(BaseModel):
    user_id: int
    method: str = 'email'

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyResetOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')

class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(min_length=20, max_length=256)
    new_password: str = Field(min_length=10, max_length=128)

def _utcnow():
    return datetime.now(timezone.utc)

def _expired(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return _utcnow() >= value

def _otp_digest(otp: str) -> str:
    return hmac_new(_require_secret().encode('utf-8'), otp.encode('utf-8'), sha256).hexdigest()

def _mask_email(email: str) -> str:
    local, domain = email.split('@', 1)
    return f'{local[:1]}***@{domain}'

def _issue_otp() -> str:
    return f'{randbelow(1_000_000):06d}'

def _replace_challenge(db: Session, purpose: str, destination: str, user_id: int | None, otp_hash: str | None, token_hash: str | None, expires_at: datetime, last_sent_at: datetime | None = None):
    db.query(AuthChallenge).filter(AuthChallenge.purpose == purpose, AuthChallenge.destination == destination).delete(synchronize_session=False)
    challenge = AuthChallenge(user_id=user_id, purpose=purpose, destination=destination, otp_hash=otp_hash, token_hash=token_hash, expires_at=expires_at, attempts=0, last_sent_at=last_sent_at)
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    return challenge

def _check_password_policy(password: str):
    if not any(c.islower() for c in password) or not any(c.isupper() for c in password) or not any(c.isdigit() for c in password):
        raise HTTPException(status_code=422, detail='Password must contain an uppercase letter, a lowercase letter and a number')

async def _send_login_otp(user: User, otp: str, db: Session):
    try:
        await run_in_threadpool(send_otp_email, user.email, otp)
    except Exception as exc:
        db.query(AuthChallenge).filter(AuthChallenge.purpose == 'login', AuthChallenge.destination == str(user.id)).delete(synchronize_session=False)
        db.commit()
        raise HTTPException(status_code=503, detail='Unable to send the verification email. Please try again later.') from exc

@router.post('/login')
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    identifier = data.username.strip().lower()
    user = db.query(User).filter(or_(func.lower(User.name) == identifier, func.lower(User.email) == identifier)).first()
    if not user or not user.is_active or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail='Invalid username or password')
    if not user.email:
        raise HTTPException(status_code=400, detail='An email address is required for login verification')
    if not user.password.startswith('$argon2id$'):
        user.password = hash_password(data.password)
        db.commit()
    now = _utcnow()
    previous = db.query(AuthChallenge).filter(AuthChallenge.purpose == 'login', AuthChallenge.destination == str(user.id)).first()
    if previous and previous.last_sent_at and now - (previous.last_sent_at.replace(tzinfo=timezone.utc) if previous.last_sent_at.tzinfo is None else previous.last_sent_at) < RESEND_COOLDOWN:
        raise HTTPException(status_code=429, detail='Please wait before requesting another verification code')
    otp = _issue_otp()
    _replace_challenge(db, 'login', str(user.id), user.id, _otp_digest(otp), None, now + OTP_TTL, now)
    await _send_login_otp(user, otp, db)
    return {'success': True, 'requires_2fa': True, 'user_id': user.id, 'masked_email': _mask_email(user.email), 'message': 'Verification code sent'}

@router.post('/verify-2fa')
async def verify_2fa(data: Verify2FARequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == data.user_id).first()
    challenge = db.query(AuthChallenge).filter(AuthChallenge.purpose == 'login', AuthChallenge.destination == str(data.user_id)).first()
    if not user or not user.is_active or not challenge:
        raise HTTPException(status_code=401, detail='Verification session is invalid or expired')
    if _expired(challenge.expires_at):
        db.delete(challenge)
        db.commit()
        raise HTTPException(status_code=401, detail='Verification code has expired')
    challenge.attempts += 1
    if challenge.attempts > MAX_OTP_ATTEMPTS:
        db.delete(challenge)
        db.commit()
        raise HTTPException(status_code=429, detail='Too many incorrect verification attempts')
    db.commit()
    if not compare_digest(_otp_digest(data.otp), challenge.otp_hash):
        raise HTTPException(status_code=401, detail='Invalid verification code')
    db.delete(challenge)
    db.commit()
    token = create_access_token(user_id=user.id, role=user.role)
    return {'success': True, 'message': '2FA verification successful', 'access_token': token, 'token_type': 'bearer', 'user_id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}

@router.post('/resend-otp')
async def resend_otp(data: ResendOtpRequest, db: Session = Depends(get_db)):
    if data.method.lower() != 'email':
        raise HTTPException(status_code=400, detail='Only email verification is currently supported')
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user or not user.is_active or not user.email:
        raise HTTPException(status_code=400, detail='Unable to resend verification code')
    now = _utcnow()
    existing = db.query(AuthChallenge).filter(AuthChallenge.purpose == 'login', AuthChallenge.destination == str(user.id)).first()
    if not existing:
        raise HTTPException(status_code=401, detail='No active login verification session')
    if existing.last_sent_at and now - (existing.last_sent_at.replace(tzinfo=timezone.utc) if existing.last_sent_at.tzinfo is None else existing.last_sent_at) < RESEND_COOLDOWN:
        raise HTTPException(status_code=429, detail='Please wait before requesting another code')
    otp = _issue_otp()
    _replace_challenge(db, 'login', str(user.id), user.id, _otp_digest(otp), None, now + OTP_TTL, now)
    await _send_login_otp(user, otp, db)
    return {'success': True, 'message': 'Verification code sent', 'method': 'email'}

@router.post('/forgot-password')
async def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user and user.is_active:
        otp = _issue_otp()
        _replace_challenge(db, 'password_reset', email, user.id, _otp_digest(otp), None, _utcnow() + OTP_TTL, _utcnow())
        try:
            await run_in_threadpool(send_password_reset_otp_email, user.email, otp)
        except Exception:
            db.query(AuthChallenge).filter(AuthChallenge.purpose == 'password_reset', AuthChallenge.destination == email).delete(synchronize_session=False)
            db.commit()
            # Keep the same response for known and unknown accounts.
    return {'success': True, 'message': 'If the account exists, a reset code has been sent.'}

@router.post('/verify-reset-otp')
async def verify_reset_otp(data: VerifyResetOtpRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    challenge = db.query(AuthChallenge).filter(AuthChallenge.purpose == 'password_reset', AuthChallenge.destination == email).first()
    if not challenge or _expired(challenge.expires_at):
        if challenge:
            db.delete(challenge)
            db.commit()
        raise HTTPException(status_code=401, detail='Invalid or expired verification code')
    challenge.attempts += 1
    if challenge.attempts > MAX_OTP_ATTEMPTS:
        db.delete(challenge)
        db.commit()
        raise HTTPException(status_code=429, detail='Too many incorrect verification attempts')
    db.commit()
    if not compare_digest(_otp_digest(data.otp), challenge.otp_hash):
        raise HTTPException(status_code=401, detail='Invalid or expired verification code')
    user_id = challenge.user_id
    db.delete(challenge)
    reset_token = token_urlsafe(32)
    token_hash = sha256(reset_token.encode('utf-8')).hexdigest()
    db.add(AuthChallenge(user_id=user_id, purpose='password_reset_token', destination=email, token_hash=token_hash, expires_at=_utcnow() + RESET_TOKEN_TTL, attempts=0))
    db.commit()
    return {'success': True, 'reset_token': reset_token}

@router.post('/reset-password')
async def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    _check_password_policy(data.new_password)
    token_hash = sha256(data.reset_token.encode('utf-8')).hexdigest()
    token_data = db.query(AuthChallenge).filter(AuthChallenge.purpose == 'password_reset_token', AuthChallenge.token_hash == token_hash).first()
    if not token_data or _expired(token_data.expires_at):
        if token_data:
            db.delete(token_data)
            db.commit()
        raise HTTPException(status_code=401, detail='Password reset session is invalid or expired')
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail='Unable to reset password')
    user.password = hash_password(data.new_password)
    db.delete(token_data)
    db.query(AuthChallenge).filter(AuthChallenge.purpose == 'login', AuthChallenge.destination == str(user.id)).delete(synchronize_session=False)
    db.commit()
    return {'success': True, 'message': 'Password reset successfully'}

@router.get('/me')
def get_authenticated_user(current_user: User = Depends(get_current_user)):
    return {'id': current_user.id, 'user_id': current_user.id, 'name': current_user.name, 'email': current_user.email, 'role': current_user.role, 'is_active': current_user.is_active}
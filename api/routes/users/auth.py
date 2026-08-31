from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from secrets import randbelow
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.worker import WorkerLoginRequest
from app.services.sms_service import send_sms
from app.services import worker_service


router = APIRouter()


# Temporary OTP storage
# {
#     user_id: {
#         "otp": "123456",
#         "expires_at": datetime
#     }
# }
otp_store = {}

class Verify2FARequest(BaseModel):
    user_id: int
    otp: str

@router.post("/verify-2fa")
async def verify_2fa(
    data: Verify2FARequest,
    db: Session = Depends(get_db)
):

    # Find user
    user = db.query(User).filter(
        User.id == data.user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Get stored OTP
    stored_otp = otp_store.get(user.id)

    if not stored_otp:
        raise HTTPException(
            status_code=401,
            detail="No active verification code"
        )

    # Check expiration
    if datetime.utcnow() > stored_otp["expires_at"]:

        otp_store.pop(user.id, None)

        raise HTTPException(
            status_code=401,
            detail="Verification code has expired"
        )

    # Check OTP
    if data.otp != stored_otp["otp"]:

        raise HTTPException(
            status_code=401,
            detail="Invalid verification code"
        )

    # OTP is correct
    otp_store.pop(user.id, None)

    return {
        "success": True,
        "message": "2FA verification successful",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role
    }

@router.post("/login")
async def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):

    # 1. Find user
    user = db.query(User).filter(
        User.name == data.username
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # 2. Check account status
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    # 3. Check password
    # Temporary plaintext comparison
    if user.password != data.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    # 4. Generate 6-digit OTP
    otp = f"{randbelow(1000000):06d}"

    # 5. Set OTP expiry to 5 minutes
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    # 6. Store OTP
    otp_store[user.id] = {
        "otp": otp,
        "expires_at": expires_at
    }

    # 7. Send OTP through Text.lk
    try:

        sms_message = (
            f"TEE verification code: {otp}. "
            "This code will expire in 5 minutes."
        )

        sms_response = await send_sms(
            recipient=user.phone_num,
            message=sms_message
        )

        print("SMS response:", sms_response)

    except Exception as e:

        # Remove OTP if SMS failed
        otp_store.pop(user.id, None)

        print("SMS sending error:", repr(e))

        raise HTTPException(
            status_code=500,
            detail="Unable to send verification code"
        )

    # 8. Return response
    return {
        "success": True,
        "message": "Verification code sent",
        "requires_2fa": True,
        "user_id": user.id
    }


@router.post("/worker-login")
async def worker_login(
    data: WorkerLoginRequest,
    db: Session = Depends(get_db)
):
    return worker_service.authenticate_worker(db, data)

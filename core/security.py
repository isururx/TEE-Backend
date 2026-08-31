import os
from datetime import datetime, timedelta, timezone

from jose import jwt
from dotenv import load_dotenv

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = "your-temporary-jwt-secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

print("JWT SECRET LOADED:", bool(SECRET_KEY))
print("JWT ALGORITHM:", ALGORITHM)

def create_access_token(user_id: int, role: str) -> str:

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire
    }

    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is not configured")

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
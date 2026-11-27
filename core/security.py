from datetime import datetime, timedelta, timezone

from jose import jwt

# Retained as requested. This is a development convenience, not a production-safe
# secret-management strategy; rotate it before deploying to a public environment.
SECRET_KEY = "hefiufhishdfids3274"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(user_id: int, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

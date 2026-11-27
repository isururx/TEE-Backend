import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from jose import jwt

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / '.env')
SECRET_KEY = os.getenv('JWT_SECRET_KEY', '').strip()
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))
PASSWORD_HASH_ITERATIONS = 310_000

def _require_secret() -> str:
    if len(SECRET_KEY) < 32:
        raise RuntimeError('JWT_SECRET_KEY must be set in .env and contain at least 32 characters.')
    return SECRET_KEY

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PASSWORD_HASH_ITERATIONS)
    return f'pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt.hex()}${derived.hex()}'

def verify_password(plain_password: str, stored_password: str) -> bool:
    if not stored_password:
        return False
    if stored_password.startswith('pbkdf2_sha256$'):
        try:
            _, iterations, salt_hex, expected_hex = stored_password.split('$', 3)
            actual = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), bytes.fromhex(salt_hex), int(iterations)).hex()
            return hmac.compare_digest(actual, expected_hex)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(plain_password, stored_password)

def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': str(user_id), 'role': role, 'type': 'access', 'iat': now, 'exp': now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)}
    return jwt.encode(payload, _require_secret(), algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, _require_secret(), algorithms=[ALGORITHM])
    if payload.get('type') != 'access' or not payload.get('sub'):
        raise ValueError('Invalid access token')
    return payload
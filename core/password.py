import hmac

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2id."""
    if not password:
        raise ValueError("Password cannot be empty")
    return password_hasher.hash(password)


def verify_password(password: str, stored_password: str) -> bool:
    """Verify Argon2 hashes and safely support legacy plain-text passwords."""
    if not password or not stored_password:
        return False

    if not stored_password.startswith("$argon2"):
        return hmac.compare_digest(password, stored_password)

    try:
        return password_hasher.verify(stored_password, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_password: str) -> bool:
    """Return True for legacy passwords or outdated Argon2 parameters."""
    if not stored_password.startswith("$argon2"):
        return True

    try:
        return password_hasher.check_needs_rehash(stored_password)
    except (TypeError, ValueError):
        return True

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


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a plain-text password against an Argon2 hash."""
    if not password or not stored_hash:
        return False

    try:
        return password_hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """Return True when the stored Argon2 hash uses outdated parameters."""
    try:
        return password_hasher.check_needs_rehash(stored_hash)
    except (TypeError, ValueError):
        return True

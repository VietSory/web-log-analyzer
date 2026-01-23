from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


_password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19_456,
    parallelism=1,
)


def hash_password(password: str) -> str:
    """Hash a password with Argon2id using OWASP-aligned minimum parameters."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True only when the supplied password matches a valid Argon2 hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_hash_needs_rehash(password_hash: str) -> bool:
    """Report whether an existing valid hash should be upgraded on next login."""
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True

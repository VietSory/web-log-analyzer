from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.security import hash_password, password_hash_needs_rehash, verify_password


def test_hash_password_uses_argon2id_and_random_salt():
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")

    assert first.startswith("$argon2id$")
    assert second.startswith("$argon2id$")
    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert verify_password("correct horse battery staple", second)


def test_verify_password_rejects_wrong_password_and_invalid_hash():
    password_hash = hash_password("a sufficiently long password")

    assert not verify_password("wrong password", password_hash)
    assert not verify_password("a sufficiently long password", "plaintext-value")


def test_current_hash_does_not_require_rehash():
    password_hash = hash_password("another sufficiently long password")

    assert not password_hash_needs_rehash(password_hash)
    assert password_hash_needs_rehash("plaintext-value")

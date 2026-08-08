from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from config import get_settings
from core.auth import create_access_token
from core.rate_limit import InMemoryRateLimiter
from core.security import hash_password, password_hash_needs_rehash, verify_password
from database import create_user, get_user_by_username, set_user_password_hash


router = APIRouter()
settings = get_settings()
_account_failure_limiter = InMemoryRateLimiter()


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=15, max_length=128)
    fullname: str | None = Field(default=None, max_length=120)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


def _account_limit_key(username: str) -> str:
    return f"login-account:{username.casefold()}"


def _account_rate_limited(username: str) -> bool:
    if not settings.rate_limit_enabled:
        return False
    return not _account_failure_limiter.check(
        _account_limit_key(username),
        limit=settings.auth_account_failure_limit,
        window_seconds=settings.rate_limit_window_seconds,
        consume=False,
    ).allowed


def _record_login_failure(username: str) -> None:
    if settings.rate_limit_enabled:
        _account_failure_limiter.check(
            _account_limit_key(username),
            limit=settings.auth_account_failure_limit,
            window_seconds=settings.rate_limit_window_seconds,
        )


def _clear_login_failures(username: str) -> None:
    _account_failure_limiter.clear(_account_limit_key(username))


@router.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    if _account_rate_limited(request.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
        )

    user = get_user_by_username(request.username)
    if not user or not verify_password(request.password, user["password_hash"]):
        _record_login_failure(request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _clear_login_failures(request.username)
    if password_hash_needs_rehash(user["password_hash"]):
        set_user_password_hash(request.username, hash_password(request.password))

    return LoginResponse(
        access_token=create_access_token(user["id"]),
        user_id=user["id"],
        username=user["username"],
    )


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    if get_user_by_username(request.username):
        raise HTTPException(status_code=409, detail="Username already exists")

    fullname = request.fullname.strip() if request.fullname else request.username
    if not fullname:
        fullname = request.username

    user_id = create_user(
        fullname,
        request.username,
        hash_password(request.password),
    )
    if not user_id:
        raise HTTPException(status_code=409, detail="Username already exists")

    return {
        "message": "Registration successful",
        "user_id": user_id,
        "username": request.username,
    }

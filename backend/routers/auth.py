from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.security import hash_password, password_hash_needs_rehash, verify_password
from database import create_user, get_user_by_username, set_user_by_username_password


router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=15, max_length=128)
    fullname: str | None = Field(default=None, max_length=120)


@router.post("/auth/login")
def login(request: LoginRequest):
    user = get_user_by_username(request.username)
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if password_hash_needs_rehash(user["password"]):
        set_user_by_username_password(request.username, hash_password(request.password))

    return {
        "message": "Login successful",
        "user_id": user["id"],
        "username": user["username"],
    }


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

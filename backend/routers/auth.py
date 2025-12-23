import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from database import get_user_by_username_password, create_user

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Request Models
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    fullname: str = None

@router.post("/auth/login")
async def login(request: LoginRequest):
    """Login user with username and password"""
    user = get_user_by_username_password(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message": "Login successful", "user_id": user["id"], "username": user["username"]}

@router.post("/auth/register")
async def register(request: RegisterRequest):
    """Register new user"""
    # Check if user already exists
    from database import get_user_by_username
    if get_user_by_username(request.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    fullname = request.fullname if request.fullname else request.username
    user_id = create_user(fullname, request.username, request.password)
    
    if not user_id:
        raise HTTPException(status_code=400, detail="Failed to create user")
    
    return {"message": "Registration successful", "user_id": user_id, "username": request.username}
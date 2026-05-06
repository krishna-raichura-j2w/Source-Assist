import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from backend.core.security import get_current_user, make_token
from backend.infra.database import (
    get_activity_stats,
    get_user_by_email,
    set_user_password,
    update_last_login,
    upsert_user,
)

from .schemas import LoginRequest, RegisterRequest
from .service import check_domain

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(body: RegisterRequest):
    email = body.email.strip().lower()
    check_domain(email)
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    existing = get_user_by_email(email)
    if existing and existing.get("password_hash"):
        raise HTTPException(status_code=409, detail="Email already registered")
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = upsert_user(email)
    set_user_password(email, hashed)
    update_last_login(str(user["id"]))
    return {"token": make_token(str(user["id"]), email), "email": email}


@router.post("/login")
def login(body: LoginRequest):
    email = body.email.strip().lower()
    check_domain(email)
    user = get_user_by_email(email)
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="No account found. Please register first.")
    if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Incorrect password")
    update_last_login(str(user["id"]))
    return {"token": make_token(str(user["id"]), email), "email": email}


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.get("/activity/me")
def my_activity(current_user: dict = Depends(get_current_user)):
    return get_activity_stats(current_user["user_id"])

import secrets

import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from backend.core.security import get_current_user, make_token
from backend.infra.database import (
    check_and_use_otp,
    get_activity_stats,
    get_cost_stats,
    get_user_by_email,
    save_otp,
    set_user_password,
    update_last_login,
    upsert_user,
)
from backend.infra.email import send_activation_email, send_password_reset_email

from .schemas import ForgotPasswordOTPRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, SendRegisterOTPRequest
from .service import check_domain

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/send-otp")
def send_register_otp(body: SendRegisterOTPRequest):
    email = body.email.strip().lower()
    check_domain(email)
    existing = get_user_by_email(email)
    if existing and existing.get("password_hash"):
        raise HTTPException(status_code=409, detail="Email already registered. Please sign in.")
    otp = str(secrets.randbelow(1_000_000)).zfill(6)
    save_otp(email, otp)
    try:
        send_activation_email(email, otp)
    except Exception as e:
        print(f"[register/send-otp] email error for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send verification email: {e}")
    return {"message": "Verification code sent to your email. It expires in 10 minutes."}


@router.post("/register")
def register(body: RegisterRequest):
    email = body.email.strip().lower()
    check_domain(email)
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not check_and_use_otp(email, body.otp.strip()):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    existing = get_user_by_email(email)
    if existing and existing.get("password_hash"):
        raise HTTPException(status_code=409, detail="Email already registered. Please sign in.")
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = upsert_user(email)
    set_user_password(email, hashed)
    update_last_login(str(user["id"]))
    return {"token": make_token(str(user["id"]), email), "email": email}


@router.post("/forgot-password/send-otp")
def forgot_password_send_otp(body: ForgotPasswordOTPRequest):
    email = body.email.strip().lower()
    check_domain(email)
    user = get_user_by_email(email)
    if not user or not user.get("password_hash"):
        return {"message": "If that email is registered, a reset code has been sent."}
    otp = str(secrets.randbelow(1_000_000)).zfill(6)
    save_otp(email, otp)
    try:
        send_password_reset_email(email, otp)
    except Exception as e:
        print(f"[forgot-password/send-otp] email error for {email}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send reset email: {e}")
    return {"message": "Reset code sent to your email. It expires in 10 minutes."}


@router.post("/forgot-password/reset")
def reset_password(body: ResetPasswordRequest):
    email = body.email.strip().lower()
    check_domain(email)
    if body.password != body.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not check_and_use_otp(email, body.otp.strip()):
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
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


@router.get("/cost/me")
def my_cost(current_user: dict = Depends(get_current_user)):
    return get_cost_stats(current_user["user_id"])


@router.get("/cost/all")
def all_cost(current_user: dict = Depends(get_current_user)):
    return get_cost_stats(user_id=None)

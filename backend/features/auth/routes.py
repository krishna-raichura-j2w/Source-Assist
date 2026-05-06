import secrets

import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from backend.core.security import get_current_user, make_token
from backend.infra.database import (
    check_and_use_otp,
    get_activity_stats,
    get_user_by_email,
    save_otp,
    set_user_password,
    update_last_login,
    upsert_user,
    validate_otp_only,
)
from backend.infra.email import send_otp_email

from .schemas import LoginRequest, OTPCheck, OTPRequest, OTPVerify
from .service import check_domain

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/request-otp")
def request_otp(body: OTPRequest):
    email = body.email.strip().lower()
    check_domain(email)
    otp = str(secrets.randbelow(1_000_000)).zfill(6)
    save_otp(email, otp)
    try:
        send_otp_email(email, otp)
    except Exception as e:
        print(f"Warning: Failed to send OTP email to {email}: {e}")
    return {"message": "OTP sent to your email. It expires in 10 minutes."}


@router.post("/check-otp")
def check_otp(body: OTPCheck):
    """Validate OTP without consuming it — used for step-2 UI verification."""
    email = body.email.strip().lower()
    check_domain(email)
    if not validate_otp_only(email, body.otp.strip()):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    return {"valid": True}


@router.post("/verify-otp")
def verify_otp(body: OTPVerify):
    email = body.email.strip().lower()
    check_domain(email)
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not check_and_use_otp(email, body.otp.strip()):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    upsert_user(email)
    set_user_password(email, hashed)
    user = get_user_by_email(email)
    update_last_login(str(user["id"]))
    return {"token": make_token(str(user["id"]), email), "email": email}


@router.post("/login")
def login(body: LoginRequest):
    email = body.email.strip().lower()
    check_domain(email)
    user = get_user_by_email(email)
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="No account found. Register using OTP first.")
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

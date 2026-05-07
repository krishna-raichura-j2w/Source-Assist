from pydantic import BaseModel


class SendRegisterOTPRequest(BaseModel):
    email: str


class RegisterRequest(BaseModel):
    email:            str
    password:         str
    confirm_password: str
    otp:              str


class LoginRequest(BaseModel):
    email:    str
    password: str


class ForgotPasswordOTPRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email:            str
    otp:              str
    password:         str
    confirm_password: str

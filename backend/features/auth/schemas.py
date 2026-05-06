from pydantic import BaseModel


class OTPRequest(BaseModel):
    email: str


class OTPCheck(BaseModel):
    email: str
    otp:   str


class OTPVerify(BaseModel):
    email:    str
    otp:      str
    password: str


class LoginRequest(BaseModel):
    email:    str
    password: str

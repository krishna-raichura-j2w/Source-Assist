from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email:            str
    password:         str
    confirm_password: str


class LoginRequest(BaseModel):
    email:    str
    password: str

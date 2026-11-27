from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class Verify2FARequest(BaseModel):
    user_id: int
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class VerifyResetOtpRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResetPasswordRequest(BaseModel):
    reset_token: str = Field(min_length=20, max_length=256)
    new_password: str = Field(min_length=6, max_length=128)

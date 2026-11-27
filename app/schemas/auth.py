from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)

class Verify2FARequest(BaseModel):
    user_id: int
    otp: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')

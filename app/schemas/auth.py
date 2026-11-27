from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class Verify2FARequest(BaseModel):
    user_id: int
    otp: str
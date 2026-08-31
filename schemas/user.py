from pydantic import BaseModel
from typing import Optional


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone_num: Optional[str] = None
    role: str
    is_active: bool = True

    class Config:
        from_attributes = True

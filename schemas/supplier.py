from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Initialize supplier schema file (Step 1)

class SupplierBase(BaseModel):
    name: str
    contact_name: Optional[str] = None
    phone_num: str
    email: EmailStr
    location: Optional[str] = None
    categories: Optional[str] = None
    status: Optional[str] = "Active"

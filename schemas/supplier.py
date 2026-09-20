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

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    phone_num: Optional[str] = None
    email: Optional[EmailStr] = None
    location: Optional[str] = None
    categories: Optional[str] = None
    status: Optional[str] = None

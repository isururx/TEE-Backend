from pydantic import BaseModel
from typing import Optional
from datetime import date


class WorkerCreate(BaseModel):
    name: str
    NIC: int
    dob: date
    address: str
    email: str
    phone_num: int
    assigned_block: Optional[int] = None
    password: str


class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    NIC: Optional[int] = None
    dob: Optional[date] = None
    address: Optional[str] = None
    email: Optional[str] = None
    phone_num: Optional[int] = None
    assigned_block: Optional[int] = None
    password: Optional[str] = None


class WorkerResponse(BaseModel):
    id: int
    name: str
    NIC: int
    dob: date
    address: str
    email: str
    phone_num: int
    assigned_block: Optional[int] = None
    assigned_block_name: Optional[str] = None
    role: str = "Worker"

    class Config:
        from_attributes = True


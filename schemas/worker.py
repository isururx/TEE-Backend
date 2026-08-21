from pydantic import BaseModel
from typing import Optional
from datetime import date


class WorkerCreate(BaseModel):
    name: str
    email: str
    phone_num: Optional[str] = None
    # Plain-text for now — hash at the service layer before storing
    password: str
    # `role` column used by auth (e.g. "user", "admin")
    role: str = "user"
    # SRS 5.1.5 mandatory fields
    NIC: Optional[str] = None
    dob: Optional[date] = None
    address: Optional[str] = None
    # Worker / Supervisor / Manager
    role_type: Optional[str] = "Worker"
    default_block_id: Optional[int] = None
    worker_code: Optional[str] = None


class WorkerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone_num: Optional[str] = None
    NIC: Optional[str] = None
    dob: Optional[date] = None
    address: Optional[str] = None
    role_type: Optional[str] = None
    default_block_id: Optional[int] = None
    worker_code: Optional[str] = None


class WorkerOut(BaseModel):
    id: int
    name: str
    email: str
    phone_num: Optional[str] = None
    role: str
    is_active: bool
    worker_code: Optional[str] = None
    NIC: Optional[str] = None
    dob: Optional[date] = None
    address: Optional[str] = None
    role_type: Optional[str] = None
    default_block_id: Optional[int] = None

    model_config = {"from_attributes": True}

from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class AttendanceCreate(BaseModel):
    worker_id: int
    date: date
    # If omitted, server time is used (for On-time / Late statuses)
    check_in_time: Optional[datetime] = None
    assigned_block_id: Optional[int] = None
    # On-time / Late / Absent / Leave
    status: str


class AttendanceOut(BaseModel):
    id: int
    worker_id: int
    worker_name: Optional[str] = None
    worker_role_type: Optional[str] = None
    date: date
    check_in_time: Optional[datetime] = None
    assigned_block_id: Optional[int] = None
    status: str

    model_config = {"from_attributes": True}


class AttendanceMetricsOut(BaseModel):
    total_workers: int
    active_count: int   # On-time + Late
    late_count: int
    absent_count: int

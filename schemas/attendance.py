from pydantic import BaseModel
from typing import Optional
from datetime import date as dt_date, time, datetime


class AttendanceCreate(BaseModel):
    worker_id: int
    date: Optional[dt_date] = None
    check_in_time: Optional[str] = None # ISO datetime or HH:MM:SS
    assigned_block_id: Optional[int] = None
    status: Optional[str] = "On-time"


class AttendanceResponse(BaseModel):
    id: int
    worker_id: int
    worker_name: str
    initials: Optional[str] = None
    worker_role_type: str = "Worker"
    date: dt_date
    check_in_time: Optional[str] = "-- : --"
    assigned_block_id: Optional[int] = None
    assigned_block: Optional[str] = "--"
    status: str = "Active"

    class Config:
        from_attributes = True


class AttendanceMetricsResponse(BaseModel):
    active: int = 0
    total: int = 0
    late: int = 0

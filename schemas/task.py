from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class TaskCreate(BaseModel):
    description: str
    deadline: Optional[datetime] = None
    priority: Optional[str] = "MEDIUM" # LOW, MEDIUM, CRITICAL
    status: Optional[str] = "QUEUED"   # QUEUED, IN PROGRESS, PENDING, ARCHIVED
    created_by: Optional[int] = 1
    block_id: Optional[int] = None
    worker_ids: Optional[List[int]] = []


class TaskUpdate(BaseModel):
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    block_id: Optional[int] = None
    worker_ids: Optional[List[int]] = None



class TaskResponse(BaseModel):
    id: int
    description: str
    deadline: Optional[str] = "--"
    priority: str = "MEDIUM"
    status: str = "QUEUED"
    created_by: int
    created_at: Optional[str] = None
    plantation_block_id: int
    plantation_block: Optional[str] = None
    assigned_worker: Optional[str] = "Unassigned"
    worker_ids: List[int] = []

    class Config:
        from_attributes = True


class AllocationItem(BaseModel):
    label: str
    percent: int
    color: str


class TaskMetricsResponse(BaseModel):
    pending: int = 0
    critical: int = 0
    inProgress: int = 0
    workforce: int = 0
    allocation: List[AllocationItem] = []

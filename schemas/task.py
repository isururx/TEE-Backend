from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TaskCreate(BaseModel):
    description: Optional[str] = None
    block_id: Optional[int] = None
    # CRITICAL / MEDIUM / LOW
    priority: str
    deadline: Optional[datetime] = None
    # List of worker IDs to assign to this task
    worker_ids: List[int] = []


class TaskStatusUpdate(BaseModel):
    # QUEUED -> IN PROGRESS -> PENDING -> ARCHIVED
    status: str


class TaskOut(BaseModel):
    id: int
    description: Optional[str] = None
    block_id: Optional[int] = None
    assigned_worker_ids: List[int] = []
    assigned_worker_names: List[str] = []
    priority: str
    status: str
    deadline: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskMetricsOut(BaseModel):
    pending_count: int
    critical_count: int
    labor_allocation: dict

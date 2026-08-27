from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TaskCreate(BaseModel):
    task_type: str
    description: Optional[str] = None
    block_id: Optional[int] = None
    # CRITICAL / MEDIUM / LOW
    priority: str
    deadline: Optional[datetime] = None
    # List of user IDs to assign to this task
    worker_ids: List[int] = []


class TaskStatusUpdate(BaseModel):
    # QUEUED → IN PROGRESS → PENDING → ARCHIVED
    status: str


class TaskOut(BaseModel):
    id: int
    task_code: Optional[str] = None
    task_type: str
    description: Optional[str] = None
    block_id: Optional[int] = None
    priority: str
    status: str
    deadline: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskMetricsOut(BaseModel):
    pending_count: int
    critical_count: int
    # Maps task_type → percentage of active tasks e.g. {"Harvesting": 45.0}
    labor_allocation: dict

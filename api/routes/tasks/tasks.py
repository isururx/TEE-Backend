from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.task import TaskCreate, TaskMetricsOut, TaskOut, TaskStatusUpdate
from app.services.tasks_services import (
    create_task_service,
    get_my_tasks_service,
    get_task_metrics_service,
    get_task_service,
    list_tasks_service,
    update_task_status_service,
)

router = APIRouter()


@router.get("/metrics", response_model=TaskMetricsOut)
def get_task_metrics(db: Session = Depends(get_db)):
    return get_task_metrics_service(db=db)


@router.get("/my-tasks", response_model=List[TaskOut])
def get_my_tasks(
    worker_id: int = Query(..., description="Worker's user ID"),
    db: Session = Depends(get_db),
):
    return get_my_tasks_service(db=db, worker_id=worker_id)


@router.get("", response_model=List[TaskOut])
def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search description"),
    db: Session = Depends(get_db),
):
    return list_tasks_service(db=db, status=status, search=search)


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    return await create_task_service(db=db, data=data)


@router.patch("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    db: Session = Depends(get_db),
):
    return update_task_status_service(db=db, task_id=task_id, data=data)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return get_task_service(db=db, task_id=task_id)

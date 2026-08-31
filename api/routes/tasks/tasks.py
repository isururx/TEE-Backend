from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskMetricsResponse
from app.services import task_service

router = APIRouter()


@router.get("", response_model=List[TaskResponse])
def get_tasks(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return task_service.get_all_tasks(db, search, status)


@router.get("/metrics", response_model=TaskMetricsResponse)
def get_task_metrics(db: Session = Depends(get_db)):
    return task_service.get_task_metrics_summary(db)


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    return task_service.create_new_task(db, data)


@router.put("/{task_id}/status", response_model=TaskResponse)
def update_task_status(task_id: int, status: str = Query(...), db: Session = Depends(get_db)):
    return task_service.update_task_status_details(db, task_id, status)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    return task_service.update_task_full(db, task_id, data)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task_service.delete_task(db, task_id)


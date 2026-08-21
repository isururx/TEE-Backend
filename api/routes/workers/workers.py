from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.worker import WorkerCreate, WorkerOut, WorkerUpdate
from app.services.workers_services import (
    create_worker_service,
    get_worker_service,
    list_workers_service,
    update_worker_service,
)

router = APIRouter()


@router.get("", response_model=List[WorkerOut])
def list_workers(
    role_type: Optional[str] = Query(None, description="Worker / Supervisor / Manager"),
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
):
    return list_workers_service(db=db, role_type=role_type, search=search)


@router.post("", response_model=WorkerOut, status_code=201)
def create_worker(data: WorkerCreate, db: Session = Depends(get_db)):
    return create_worker_service(db=db, data=data)


@router.get("/{id}", response_model=WorkerOut)
def get_worker(id: int, db: Session = Depends(get_db)):
    return get_worker_service(db=db, worker_id=id)


@router.put("/{id}", response_model=WorkerOut)
def update_worker(
    id: int,
    data: WorkerUpdate,
    db: Session = Depends(get_db),
):
    return update_worker_service(db=db, worker_id=id, data=data)

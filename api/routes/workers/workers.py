from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.schemas.worker import WorkerCreate, WorkerUpdate, WorkerResponse
from app.services import worker_service

router = APIRouter()


@router.get("", response_model=List[WorkerResponse])
def get_workers(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return worker_service.get_all_workers(db, search)


@router.get("/{worker_id}", response_model=WorkerResponse)
def get_worker(worker_id: int, db: Session = Depends(get_db)):
    return worker_service.get_worker_by_id(db, worker_id)


@router.post("", response_model=WorkerResponse, status_code=201)
def create_worker(data: WorkerCreate, db: Session = Depends(get_db)):
    return worker_service.register_new_worker(db, data)


@router.put("/{worker_id}", response_model=WorkerResponse)
def update_worker(worker_id: int, data: WorkerUpdate, db: Session = Depends(get_db)):
    return worker_service.update_worker_profile(db, worker_id, data)


@router.delete("/{worker_id}", status_code=204)
def delete_worker(worker_id: int, db: Session = Depends(get_db)):
    return worker_service.delete_worker_profile(db, worker_id)

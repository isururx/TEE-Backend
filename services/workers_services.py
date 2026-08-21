from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.worker import Worker
from app.schemas.worker import WorkerCreate, WorkerUpdate


def list_workers_service(
    db: Session,
    role_type: Optional[str] = None,
    search: Optional[str] = None,
):
    query = db.query(Worker).filter(Worker.is_active == True)  # noqa: E712

    if role_type:
        query = query.filter(Worker.role_type == role_type)

    if search:
        query = query.filter(Worker.name.ilike(f"%{search}%"))

    return query.order_by(Worker.name).all()


def create_worker_service(db: Session, data: WorkerCreate):
    if db.query(Worker).filter(Worker.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if data.NIC and db.query(Worker).filter(Worker.NIC == data.NIC).first():
        raise HTTPException(status_code=400, detail="NIC already registered")

    if data.worker_code and db.query(Worker).filter(
        Worker.worker_code == data.worker_code
    ).first():
        raise HTTPException(status_code=400, detail="Worker code already in use")

    worker = Worker(**_model_fields_for_worker(data.model_dump()))
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


def get_worker_service(db: Session, worker_id: int):
    return _get_worker_or_404(db, worker_id)


def update_worker_service(db: Session, worker_id: int, data: WorkerUpdate):
    worker = _get_worker_or_404(db, worker_id)

    for field, value in _model_fields_for_worker(data.model_dump(exclude_none=True)).items():
        setattr(worker, field, value)

    db.commit()
    db.refresh(worker)
    return worker


def _get_worker_or_404(db: Session, worker_id: int) -> Worker:
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")
    return worker


def _model_fields_for_worker(values: dict):
    return {
        field: value
        for field, value in values.items()
        if hasattr(Worker, field)
    }

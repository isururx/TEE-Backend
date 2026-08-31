from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException

from app.db.models.worker import Worker
from app.db.models.plantation_block import PlantationBlock
from app.schemas.worker import WorkerCreate, WorkerUpdate, WorkerLoginRequest


def format_worker(worker: Worker, db: Session) -> dict:
    block_name = "Unassigned"
    if worker.assigned_block:
        block = db.query(PlantationBlock).filter(PlantationBlock.id == worker.assigned_block).first()
        if block:
            block_name = f"Block {block.id}"

    return {
        "id": worker.id,
        "name": worker.name,
        "NIC": worker.NIC,
        "dob": worker.dob,
        "address": worker.address,
        "email": worker.email,
        "phone_num": worker.phone_num,
        "assigned_block": worker.assigned_block,
        "assigned_block_name": block_name,
        "role": "Worker"
    }


def get_all_workers(db: Session, search: Optional[str] = None) -> List[dict]:
    query = db.query(Worker)
    if search:
        search_pat = f"%{search.strip()}%"
        query = query.filter(
            (Worker.name.ilike(search_pat)) |
            (Worker.email.ilike(search_pat)) |
            (Worker.address.ilike(search_pat))
        )
    workers = query.order_by(Worker.id.asc()).all()
    return [format_worker(w, db) for w in workers]


def get_worker_by_id(db: Session, worker_id: int) -> dict:
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")
    return format_worker(worker, db)


def register_new_worker(db: Session, data: WorkerCreate) -> dict:
    existing = db.query(Worker).filter(Worker.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Worker email already registered")

    if data.assigned_block:
        block = db.query(PlantationBlock).filter(PlantationBlock.id == data.assigned_block).first()
        if not block:
            raise HTTPException(status_code=400, detail=f"Block {data.assigned_block} not found")

    new_worker = Worker(
        name=data.name,
        NIC=data.NIC,
        dob=data.dob,
        address=data.address,
        email=data.email,
        phone_num=data.phone_num,
        assigned_block=data.assigned_block,
        password=data.password,
    )
    db.add(new_worker)
    db.commit()
    db.refresh(new_worker)

    return format_worker(new_worker, db)


def update_worker_profile(db: Session, worker_id: int, data: WorkerUpdate) -> dict:
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")

    if data.name is not None:
        worker.name = data.name
    if data.NIC is not None:
        worker.NIC = data.NIC
    if data.dob is not None:
        worker.dob = data.dob
    if data.address is not None:
        worker.address = data.address
    if data.email is not None:
        worker.email = data.email
    if data.phone_num is not None:
        worker.phone_num = data.phone_num
    if data.assigned_block is not None:
        worker.assigned_block = data.assigned_block
    if data.password is not None:
        worker.password = data.password

    db.commit()
    db.refresh(worker)
    return format_worker(worker, db)


def delete_worker_profile(db: Session, worker_id: int) -> None:
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")

    db.delete(worker)
    db.commit()
    return None


def authenticate_worker(db: Session, data: WorkerLoginRequest) -> dict:
    worker = db.query(Worker).filter(Worker.id == data.worker_id).first()

    if not worker or worker.password != data.password:
        raise HTTPException(
            status_code=401,
            detail="Invalid Worker ID or password"
        )

    return {
        "success": True,
        "message": "Worker authenticated successfully",
        "requires_2fa": False,
        "worker": {
            "id": worker.id,
            "name": worker.name,
            "email": worker.email,
            "assigned_block": worker.assigned_block,
            "role": "Worker"
        }
    }

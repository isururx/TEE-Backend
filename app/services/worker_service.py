from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from fastapi import HTTPException

from app.db.models.worker import Worker
from app.db.models.user import User
from app.db.models.plantation_block import PlantationBlock
from app.schemas.worker import WorkerCreate, WorkerUpdate


def _sync_sequence(db: Session, table: str = "users"):
    """
    Synchronizes PostgreSQL primary key auto-increment sequence
    with the current max(id) in the table to prevent duplicate key errors.
    """
    try:
        seq = db.execute(text(f"SELECT pg_get_serial_sequence('{table}', 'id')")).scalar()
        if not seq:
            seq = f"{table}_id_seq"
        max_id = db.execute(text(f"SELECT coalesce(max(id), 0) FROM {table}")).scalar() or 0
        if max_id > 0:
            db.execute(text(f"SELECT setval('{seq}', {max_id}, true)"))
        else:
            db.execute(text(f"SELECT setval('{seq}', 1, false)"))
    except Exception:
        pass


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
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    existing_worker = db.query(Worker).filter(Worker.email == data.email).first()
    if existing_worker:
        raise HTTPException(status_code=400, detail="Worker email already registered")

    if data.assigned_block:
        block = db.query(PlantationBlock).filter(PlantationBlock.id == data.assigned_block).first()
        if not block:
            raise HTTPException(status_code=400, detail=f"Block {data.assigned_block} not found")

    # Sync sequence to ensure nextval is greater than current max(id)
    _sync_sequence(db, "users")

    # 1. Create User row in users table first
    new_user = User(
        name=data.name,
        email=data.email,
        phone_num=str(data.phone_num),
        password=data.password,
        role="Worker",
        is_active=True,
    )
    db.add(new_user)
    try:
        db.flush()  # Generates new_user.id
    except Exception:
        db.rollback()
        # Force re-sync sequence and retry
        _sync_sequence(db, "users")
        new_user = User(
            name=data.name,
            email=data.email,
            phone_num=str(data.phone_num),
            password=data.password,
            role="Worker",
            is_active=True,
        )
        db.add(new_user)
        db.flush()

    # 2. Create Worker row with id = new_user.id
    new_worker = Worker(
        id=new_user.id,
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

    user = db.query(User).filter(User.id == worker_id).first()

    if data.name is not None:
        worker.name = data.name
        if user:
            user.name = data.name
    if data.NIC is not None:
        worker.NIC = data.NIC
    if data.dob is not None:
        worker.dob = data.dob
    if data.address is not None:
        worker.address = data.address
    if data.email is not None:
        worker.email = data.email
        if user:
            user.email = data.email
    if data.phone_num is not None:
        worker.phone_num = data.phone_num
        if user:
            user.phone_num = str(data.phone_num)
    if data.assigned_block is not None:
        worker.assigned_block = data.assigned_block
    if data.password is not None:
        worker.password = data.password
        if user:
            user.password = data.password

    db.commit()
    db.refresh(worker)
    return format_worker(worker, db)


def delete_worker_profile(db: Session, worker_id: int) -> None:
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")

    user = db.query(User).filter(User.id == worker_id).first()

    db.delete(worker)
    if user:
        db.delete(user)
    db.commit()
    return None


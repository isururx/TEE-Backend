from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.user import User
from app.schemas.worker import WorkerCreate, WorkerOut, WorkerUpdate

router = APIRouter()


# ── GET /api/workers ─────────────────────────────────────────────────────────

@router.get("", response_model=List[WorkerOut])
def list_workers(
    role_type: Optional[str] = Query(None, description="Worker / Supervisor / Manager"),
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
):
    """Return active workers — used by task & attendance dropdowns."""
    query = db.query(User).filter(User.is_active == True)  # noqa: E712

    if role_type:
        query = query.filter(User.role_type == role_type)

    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    return query.order_by(User.name).all()


# ── POST /api/workers ────────────────────────────────────────────────────────

@router.post("", response_model=WorkerOut, status_code=201)
def create_worker(data: WorkerCreate, db: Session = Depends(get_db)):
    """
    Register a new worker (SRS 5.1.5).
    Passwords are stored as plain-text for now — hash them here once
    bcrypt/passlib is added to the project.
    """
    # Email uniqueness check
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # NIC uniqueness check (if provided)
    if data.NIC and db.query(User).filter(User.NIC == data.NIC).first():
        raise HTTPException(status_code=400, detail="NIC already registered")

    # worker_code uniqueness check (if provided)
    if data.worker_code and db.query(User).filter(
        User.worker_code == data.worker_code
    ).first():
        raise HTTPException(status_code=400, detail="Worker code already in use")

    worker = User(**data.model_dump())
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


# ── GET /api/workers/{worker_id} ─────────────────────────────────────────────

@router.get("/{worker_id}", response_model=WorkerOut)
def get_worker(worker_id: int, db: Session = Depends(get_db)):
    return _get_worker_or_404(worker_id, db)


# ── PUT /api/workers/{worker_id} ─────────────────────────────────────────────

@router.put("/{worker_id}", response_model=WorkerOut)
def update_worker(
    worker_id: int,
    data: WorkerUpdate,
    db: Session = Depends(get_db),
):
    worker = _get_worker_or_404(worker_id, db)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(worker, field, value)

    db.commit()
    db.refresh(worker)
    return worker


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_worker_or_404(worker_id: int, db: Session) -> User:
    worker = db.query(User).filter(User.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")
    return worker

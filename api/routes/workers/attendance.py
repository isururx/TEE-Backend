from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.attendance import Attendance
from app.db.models.user import User
from app.schemas.attendance import AttendanceCreate, AttendanceMetricsOut, AttendanceOut

router = APIRouter()


# ── NOTE: /metrics MUST be declared before /{attendance_id} ─────────────────

# ── GET /api/attendance/metrics ──────────────────────────────────────────────

@router.get("/metrics", response_model=AttendanceMetricsOut)
def get_attendance_metrics(
    target_date: Optional[date] = Query(None, description="Date (YYYY-MM-DD), defaults to today"),
    db: Session = Depends(get_db),
):
    """Return active/late/absent counts for the workforce ratio cards."""
    if not target_date:
        target_date = date.today()

    total_workers = (
        db.query(func.count(User.id))
        .filter(User.is_active == True)  # noqa: E712
        .scalar()
    )

    active_count = (
        db.query(func.count(Attendance.id))
        .filter(
            Attendance.date == target_date,
            Attendance.status.in_(["On-time", "Late"]),
        )
        .scalar()
    )

    late_count = (
        db.query(func.count(Attendance.id))
        .filter(Attendance.date == target_date, Attendance.status == "Late")
        .scalar()
    )

    absent_count = (
        db.query(func.count(Attendance.id))
        .filter(Attendance.date == target_date, Attendance.status == "Absent")
        .scalar()
    )

    return AttendanceMetricsOut(
        total_workers=total_workers,
        active_count=active_count,
        late_count=late_count,
        absent_count=absent_count,
    )


# ── GET /api/attendance ──────────────────────────────────────────────────────

@router.get("", response_model=List[AttendanceOut])
def list_attendance(
    target_date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="On-time / Late / Absent / Leave"),
    search: Optional[str] = Query(None, description="Search by worker name"),
    db: Session = Depends(get_db),
):
    query = db.query(Attendance)

    if target_date:
        query = query.filter(Attendance.date == target_date)

    if status:
        query = query.filter(Attendance.status == status)

    if search:
        # Join User to search by name
        query = query.join(User, Attendance.worker_id == User.id).filter(
            User.name.ilike(f"%{search}%")
        )

    return query.order_by(Attendance.date.desc()).all()


# ── POST /api/attendance ─────────────────────────────────────────────────────

@router.post("", response_model=AttendanceOut, status_code=201)
def log_attendance(data: AttendanceCreate, db: Session = Depends(get_db)):
    """
    Log attendance for a worker.
    - check_in_time defaults to current UTC time for On-time/Late statuses.
    - check_in_time is set to None for Absent/Leave (no physical check-in).
    """
    worker = db.query(User).filter(User.id == data.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {data.worker_id} not found")

    # Determine check_in_time
    if data.status in ("On-time", "Late"):
        check_in_time = data.check_in_time or datetime.utcnow()
    else:
        check_in_time = None  # Absent / Leave — no physical check-in

    record = Attendance(
        worker_id=data.worker_id,
        date=data.date,
        check_in_time=check_in_time,
        assigned_block_id=data.assigned_block_id,
        status=data.status,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── GET /api/attendance/{attendance_id} ──────────────────────────────────────

@router.get("/{attendance_id}", response_model=AttendanceOut)
def get_attendance(attendance_id: int, db: Session = Depends(get_db)):
    record = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not record:
        raise HTTPException(
            status_code=404, detail=f"Attendance record {attendance_id} not found"
        )
    return record

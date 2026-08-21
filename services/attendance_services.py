from datetime import date, datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.attendance import Attendance
from app.db.models.worker import Worker
from app.schemas.attendance import AttendanceCreate, AttendanceMetricsOut


def get_attendance_metrics_service(
    db: Session,
    target_date: Optional[date] = None,
):
    if not target_date:
        target_date = date.today()

    total_workers = (
        db.query(func.count(Worker.id))
        .filter(Worker.is_active == True)  # noqa: E712
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


def list_attendance_service(
    db: Session,
    target_date: Optional[date] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    query = db.query(Attendance)

    if target_date:
        query = query.filter(Attendance.date == target_date)

    if status:
        query = query.filter(Attendance.status == status)

    if search:
        query = query.join(Worker, Attendance.worker_id == Worker.id).filter(
            Worker.name.ilike(f"%{search}%")
        )

    records = query.order_by(Attendance.date.desc()).all()
    return [_build_attendance_response(db, record) for record in records]


def log_attendance_service(db: Session, data: AttendanceCreate):
    worker = db.query(Worker).filter(Worker.id == data.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {data.worker_id} not found")

    if data.status in ("On-time", "Late"):
        check_in_time = data.check_in_time or datetime.utcnow()
    else:
        check_in_time = None

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
    return _build_attendance_response(db, record)


def get_attendance_service(db: Session, attendance_id: int):
    record = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Attendance record {attendance_id} not found",
        )
    return _build_attendance_response(db, record)


def _build_attendance_response(db: Session, record: Attendance):
    worker = db.query(Worker).filter(Worker.id == record.worker_id).first()

    return {
        "id": record.id,
        "worker_id": record.worker_id,
        "worker_name": worker.name if worker else None,
        "worker_role_type": worker.role_type if worker else None,
        "date": record.date,
        "check_in_time": record.check_in_time,
        "assigned_block_id": record.assigned_block_id,
        "status": record.status,
    }

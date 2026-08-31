from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, time, datetime
from fastapi import HTTPException

from app.db.models.attendance import Attendance
from app.db.models.worker import Worker
from app.schemas.attendance import AttendanceCreate


def get_initials(name: str) -> str:
    parts = (name or "?").split()
    return "".join(p[0] for p in parts)[:2].upper()


def format_attendance(att: Attendance, db: Session) -> dict:
    worker = db.query(Worker).filter(Worker.id == att.worker_id).first()
    worker_name = worker.name if worker else "Unknown Worker"
    block_str = f"Block {att.assigned_block_id}" if att.assigned_block_id else "--"

    formatted_time = "-- : --"
    if att.check_in_time:
        try:
            formatted_time = att.check_in_time.strftime("%I:%M %p")
        except AttributeError:
            formatted_time = str(att.check_in_time)

    return {
        "id": att.id,
        "worker_id": att.worker_id,
        "worker_name": worker_name,
        "initials": get_initials(worker_name),
        "worker_role_type": "Worker",
        "date": att.Date,
        "check_in_time": formatted_time,
        "assigned_block_id": att.assigned_block_id,
        "assigned_block": block_str,
        "status": att.status,
    }


def get_attendance_records(
    db: Session,
    target_date: Optional[date] = None,
    search: Optional[str] = None,
    status: Optional[str] = None
) -> List[dict]:
    query_date = target_date or date.today()
    query = db.query(Attendance).filter(Attendance.Date == query_date)

    if status and status != "ALL":
        query = query.filter(Attendance.status.ilike(status))

    records = query.order_by(Attendance.id.desc()).all()
    results = [format_attendance(r, db) for r in records]

    if search:
        s = search.strip().lower()
        results = [
            r for r in results
            if s in r["worker_name"].lower() or s in str(r["worker_id"]) or s in r["assigned_block"].lower()
        ]

    return results


def get_attendance_metrics_summary(db: Session, target_date: Optional[date] = None) -> dict:
    query_date = target_date or date.today()

    total_workers = db.query(func.count(Worker.id)).scalar() or 0
    active_count = db.query(func.count(Attendance.id)).filter(
        Attendance.Date == query_date,
        Attendance.status.in_(["Active", "On-time", "Late"])
    ).scalar() or 0
    late_count = db.query(func.count(Attendance.id)).filter(
        Attendance.Date == query_date,
        Attendance.status == "Late"
    ).scalar() or 0

    return {
        "active": active_count,
        "total": total_workers,
        "late": late_count
    }


def log_worker_attendance(db: Session, data: AttendanceCreate) -> dict:
    worker = db.query(Worker).filter(Worker.id == data.worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail=f"Worker {data.worker_id} not found")

    att_date = data.date or date.today()

    parsed_time = datetime.now().time()
    if data.check_in_time:
        try:
            if "T" in data.check_in_time:
                parsed_time = datetime.fromisoformat(data.check_in_time.replace("Z", "+00:00")).time()
            elif ":" in data.check_in_time:
                time_parts = data.check_in_time.split(":")
                parsed_time = time(hour=int(time_parts[0]), minute=int(time_parts[1]))
        except Exception:
            parsed_time = datetime.now().time()

    block_id = data.assigned_block_id or worker.assigned_block

    existing = db.query(Attendance).filter(
        Attendance.worker_id == data.worker_id,
        Attendance.Date == att_date
    ).first()

    if existing:
        existing.check_in_time = parsed_time
        existing.assigned_block_id = block_id
        existing.status = data.status or "On-time"
        db.commit()
        db.refresh(existing)
        return format_attendance(existing, db)

    new_att = Attendance(
        worker_id=data.worker_id,
        Date=att_date,
        check_in_time=parsed_time,
        assigned_block_id=block_id,
        status=data.status or "On-time",
    )
    db.add(new_att)
    db.commit()
    db.refresh(new_att)

    return format_attendance(new_att, db)

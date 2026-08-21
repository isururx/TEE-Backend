from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.attendance import AttendanceCreate, AttendanceMetricsOut, AttendanceOut
from app.services.attendance_services import (
    get_attendance_metrics_service,
    get_attendance_service,
    list_attendance_service,
    log_attendance_service,
)

router = APIRouter()


@router.get("/metrics", response_model=AttendanceMetricsOut)
def get_attendance_metrics(
    target_date: Optional[date] = Query(None, description="Date (YYYY-MM-DD), defaults to today"),
    db: Session = Depends(get_db),
):
    return get_attendance_metrics_service(db=db, target_date=target_date)


@router.get("", response_model=List[AttendanceOut])
def list_attendance(
    target_date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="On-time / Late / Absent / Leave"),
    search: Optional[str] = Query(None, description="Search by worker name"),
    db: Session = Depends(get_db),
):
    return list_attendance_service(
        db=db,
        target_date=target_date,
        status=status,
        search=search,
    )


@router.post("", response_model=AttendanceOut, status_code=201)
def log_attendance(data: AttendanceCreate, db: Session = Depends(get_db)):
    return log_attendance_service(db=db, data=data)


@router.get("/{attendance_id}", response_model=AttendanceOut)
def get_attendance(attendance_id: int, db: Session = Depends(get_db)):
    return get_attendance_service(db=db, attendance_id=attendance_id)

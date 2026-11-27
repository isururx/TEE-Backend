from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.db.database import get_db
from app.schemas.attendance import AttendanceCreate, AttendanceResponse, AttendanceMetricsResponse
from app.services import attendance_service

router = APIRouter()


@router.get("", response_model=List[AttendanceResponse])
def get_attendance(
    target_date: Optional[date] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return attendance_service.get_attendance_records(db, target_date, search, status)


@router.get("/metrics", response_model=AttendanceMetricsResponse)
def get_attendance_metrics(
    target_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    return attendance_service.get_attendance_metrics_summary(db, target_date)


@router.post("", response_model=AttendanceResponse, status_code=201)
def log_attendance(data: AttendanceCreate, db: Session = Depends(get_db)):
    return attendance_service.log_worker_attendance(db, data)

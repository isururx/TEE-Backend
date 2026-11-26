from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.activity_log import ActivityLog
from app.db.models.attendance import Attendance
from app.db.models.detection import DiseaseDetection
from app.db.models.inventory_item import InventoryItem
from app.db.models.plantation_block import PlantationBlock
from app.db.models.supplier import Supplier
from app.db.models.task import Task
from app.db.models.user import User
from app.db.models.worker import Worker

router = APIRouter()


class SupplierCreate(BaseModel):
    name: str
    category: Optional[str] = "General Supplies"
    contact: Optional[str] = "N/A"
    email: Optional[str] = ""


def _task_progress(status: Optional[str]) -> int:
    normalized = (status or "").upper()
    if normalized in ("FINISHED", "COMPLETED"):
        return 100
    if normalized in ("IN PROGRESS", "IN_PROGRESS", "ONGOING"):
        return 50
    return 0


@router.get("/admin")
def get_admin_dashboard(db: Session = Depends(get_db)):
    """Return live metrics and recent activity logs for AdminDashboard."""
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0
    estate_managers = (
        db.query(func.count(User.id))
        .filter(User.is_active == True, User.role.ilike("%manager%"))
        .scalar()
        or 0
    )
    supervisors = (
        db.query(func.count(User.id))
        .filter(User.is_active == True, User.role.ilike("%supervisor%"))
        .scalar()
        or 0
    )
    total_blocks = db.query(func.count(PlantationBlock.id)).scalar() or 0

    logs = (
        db.query(ActivityLog)
        .order_by(ActivityLog.timestamp.desc())
        .limit(10)
        .all()
    )
    recent_logs = [
        {
            "id": log.id,
            "user": log.user.name if log.user else "System",
            "role": log.user.role if log.user else "System",
            "action": log.action,
            "details": log.details,
            "time": log.timestamp.strftime("%Y-%m-%d %H:%M") if log.timestamp else "",
        }
        for log in logs
    ]

    return {
        "active_users": active_users,
        "total_users": total_users,
        "estate_managers": estate_managers,
        "supervisors": supervisors,
        "total_blocks": total_blocks,
        "system_health": "99.9%",
        "recent_logs": recent_logs,
    }


@router.get("/operations")
def get_operations_dashboard(db: Session = Depends(get_db)):
    """Return live workers, suppliers, low-stock items, tasks, blocks, and attendance for Manager/Supervisor dashboards."""
    workers_rows = db.query(Worker).order_by(Worker.id.asc()).all()
    workers = [
        {
            "id": f"W{w.id:03d}",
            "raw_id": w.id,
            "name": w.name,
            "role": "Field Worker",
            "block": f"Block {w.assigned_block}" if w.assigned_block else "Unassigned",
            "status": "Active",
        }
        for w in workers_rows
    ]

    supervisors_rows = (
        db.query(User)
        .filter(User.is_active == True, User.role.ilike("%supervisor%"))
        .order_by(User.id.asc())
        .all()
    )
    supervisors = [{"id": u.id, "name": u.name} for u in supervisors_rows]

    blocks_rows = db.query(PlantationBlock).order_by(PlantationBlock.id.asc()).all()
    blocks = [{"id": b.id, "label": f"Block {b.id}"} for b in blocks_rows]

    suppliers_rows = db.query(Supplier).order_by(Supplier.id.asc()).all()
    suppliers = [
        {
            "id": s.id,
            "name": s.name,
            "category": s.categories or "General Supplies",
            "contact": s.phone_num or "N/A",
        }
        for s in suppliers_rows
    ]

    low_stock_rows = (
        db.query(InventoryItem)
        .filter(InventoryItem.quantity <= InventoryItem.reorder_point)
        .order_by(InventoryItem.quantity.asc())
        .all()
    )
    low_stock_items = [
        {
            "id": item.id,
            "item": item.name,
            "quantity": f"{item.quantity}",
            "threshold": f"{item.reorder_point}",
            "level": "Critical" if item.quantity <= max(1, item.reorder_point // 2) else "Warning",
            "statusClass": "badge-danger" if item.quantity <= max(1, item.reorder_point // 2) else "badge-warning",
        }
        for item in low_stock_rows
    ]

    tasks_rows = db.query(Task).order_by(Task.created_at.desc()).limit(20).all()
    assigned_tasks = []
    for t in tasks_rows:
        assignee_names = ", ".join(w.name for w in t.workers) if t.workers else "Unassigned"
        assigned_tasks.append(
            {
                "id": f"TSK-{t.id}",
                "raw_id": t.id,
                "title": t.description,
                "assignee": assignee_names,
                "role": "Worker",
                "progress": _task_progress(t.status),
                "priority": (t.priority or "MEDIUM").capitalize(),
                "status": t.status,
            }
        )

    total_workers = len(workers_rows)
    present_today = (
        db.query(func.count(func.distinct(Attendance.worker_id)))
        .filter(Attendance.Date == date.today())
        .scalar()
        or 0
    )
    attendance_pct = round((present_today / total_workers) * 100) if total_workers > 0 else 0

    return {
        "workers": workers,
        "supervisors": supervisors,
        "blocks": blocks,
        "suppliers": suppliers,
        "low_stock_items": low_stock_items,
        "assigned_tasks": assigned_tasks,
        "attendance_percentage": attendance_pct,
    }


@router.get("/worker/{worker_id}")
def get_worker_dashboard_summary(worker_id: int, db: Session = Depends(get_db)):
    """Return today's attendance/shift summary for a worker."""
    today_att = (
        db.query(Attendance)
        .filter(Attendance.worker_id == worker_id, Attendance.Date == date.today())
        .order_by(Attendance.id.desc())
        .first()
    )
    return {
        "clock_in_time": today_att.check_in_time.strftime("%I:%M %p") if today_att and today_att.check_in_time else "Not Clocked In",
        "status": today_att.status if today_att else "Off Duty",
    }


@router.post("/suppliers")
def create_dashboard_supplier(data: SupplierCreate, db: Session = Depends(get_db)):
    supplier = Supplier(
        name=data.name,
        categories=data.category or "General Supplies",
        phone_num=data.contact or "N/A",
        email=data.email or "",
        status="Active",
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return {
        "id": supplier.id,
        "name": supplier.name,
        "category": supplier.categories or "General Supplies",
        "contact": supplier.phone_num or "N/A",
    }


@router.delete("/suppliers/{supplier_id}")
def delete_dashboard_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    db.delete(supplier)
    db.commit()
    return {"success": True}


@router.delete("/disease-history/{block_id}")
def clear_block_disease_history(block_id: int, db: Session = Depends(get_db)):
    deleted = (
        db.query(DiseaseDetection)
        .filter(DiseaseDetection.block_id == block_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"success": True, "deleted_count": deleted}

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException

from app.db.models.task import Task, TaskWorker
from app.db.models.worker import Worker
from app.db.models.plantation_block import PlantationBlock
from app.schemas.task import TaskCreate, AllocationItem


def format_task(task: Task, db: Session) -> dict:
    worker_rows = (
        db.query(Worker)
        .join(TaskWorker, TaskWorker.worker_id == Worker.id)
        .filter(TaskWorker.task_id == task.id)
        .all()
    )
    worker_names = [w.name for w in worker_rows]
    assigned_worker_str = ", ".join(worker_names) if worker_names else "Unassigned"

    block_str = f"Block {task.plantation_block_id}" if task.plantation_block_id else "Unassigned"

    return {
        "id": task.id,
        "description": task.description,
        "deadline": task.deadline.strftime("%b %d, %Y") if task.deadline else "--",
        "priority": task.priority,
        "status": task.status,
        "created_by": task.created_by,
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M") if task.created_at else None,
        "plantation_block_id": task.plantation_block_id,
        "plantation_block": block_str,
        "assigned_worker": assigned_worker_str,
        "worker_ids": [w.id for w in worker_rows]
    }


def get_all_tasks(db: Session, search: Optional[str] = None, status: Optional[str] = None) -> List[dict]:
    query = db.query(Task)
    if status and status != "ALL":
        query = query.filter(Task.status.ilike(status))

    if search:
        search_pat = f"%{search.strip()}%"
        query = query.filter(
            (Task.description.ilike(search_pat)) |
            (Task.priority.ilike(search_pat))
        )

    tasks = query.order_by(Task.created_at.desc()).all()
    return [format_task(t, db) for t in tasks]


def get_task_metrics_summary(db: Session) -> dict:
    pending_count = db.query(func.count(Task.id)).filter(
        Task.status.in_(["QUEUED", "PENDING"])
    ).scalar() or 0

    critical_count = db.query(func.count(Task.id)).filter(
        Task.status.in_(["QUEUED", "PENDING"]),
        Task.priority == "CRITICAL"
    ).scalar() or 0

    in_progress_count = db.query(func.count(Task.id)).filter(
        Task.status == "IN PROGRESS"
    ).scalar() or 0

    workforce_count = db.query(func.count(func.distinct(TaskWorker.worker_id))).join(
        Task, Task.id == TaskWorker.task_id
    ).filter(
        Task.status == "IN PROGRESS"
    ).scalar() or 0

    if workforce_count == 0:
        workforce_count = db.query(func.count(Worker.id)).scalar() or 0

    total_tasks = db.query(func.count(Task.id)).scalar() or 1
    harvest_count = db.query(func.count(Task.id)).filter(Task.description.ilike("%harvest%")).scalar() or 0
    maint_count = db.query(func.count(Task.id)).filter(
        (Task.description.ilike("%prun%")) |
        (Task.description.ilike("%spray%")) |
        (Task.description.ilike("%fertiliz%")) |
        (Task.description.ilike("%weedTest%"))
    ).scalar() or 0
    quality_count = db.query(func.count(Task.id)).filter(
        (Task.description.ilike("%inspect%")) |
        (Task.description.ilike("%test%")) |
        (Task.description.ilike("%check%"))
    ).scalar() or 0

    h_pct = int(round((harvest_count / total_tasks) * 100)) if harvest_count else 45
    m_pct = int(round((maint_count / total_tasks) * 100)) if maint_count else 25
    q_pct = int(round((quality_count / total_tasks) * 100)) if quality_count else 15
    r_pct = max(0, 100 - (h_pct + m_pct + q_pct))

    allocation = [
        AllocationItem(label="Harvesting", percent=h_pct, color="#1B5E20"),
        AllocationItem(label="Maintenance", percent=m_pct, color="#4CAF50"),
        AllocationItem(label="Quality Check", percent=q_pct, color="#81C784"),
        AllocationItem(label="Rest / Buffer", percent=r_pct, color="#C8E6C9"),
    ]

    return {
        "pending": pending_count,
        "critical": critical_count,
        "inProgress": in_progress_count,
        "workforce": workforce_count,
        "allocation": allocation,
    }


def create_new_task(db: Session, data: TaskCreate) -> dict:
    block_id = data.block_id
    if not block_id:
        first_block = db.query(PlantationBlock).first()
        if first_block:
            block_id = first_block.id
        else:
            raise HTTPException(status_code=400, detail="No plantation blocks exist to assign task to")

    new_task = Task(
        description=data.description,
        deadline=data.deadline,
        priority=data.priority or "MEDIUM",
        status=data.status or "QUEUED",
        created_by=data.created_by or 1,
        created_at=datetime.utcnow(),
        plantation_block_id=block_id,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    if data.worker_ids:
        for w_id in data.worker_ids:
            tw = TaskWorker(task_id=new_task.id, worker_id=w_id)
            db.add(tw)
        db.commit()

    return format_task(new_task, db)


def update_task_status_details(db: Session, task_id: int, status: str) -> dict:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    task.status = status.upper()
    db.commit()
    db.refresh(task)
    return format_task(task, db)


def delete_task(db: Session, task_id: int) -> None:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Delete junction rows first to avoid FK constraint violations
    db.query(TaskWorker).filter(TaskWorker.task_id == task_id).delete()
    db.delete(task)
    db.commit()


def update_task_full(db: Session, task_id: int, data) -> dict:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if data.description is not None:
        task.description = data.description
    if data.deadline is not None:
        task.deadline = data.deadline
    if data.priority is not None:
        task.priority = data.priority.upper()
    if data.status is not None:
        task.status = data.status.upper()
    if data.block_id is not None:
        task.plantation_block_id = data.block_id

    db.commit()

    # Re-sync worker assignments if worker_ids provided
    if data.worker_ids is not None:
        db.query(TaskWorker).filter(TaskWorker.task_id == task_id).delete()
        for w_id in data.worker_ids:
            db.add(TaskWorker(task_id=task_id, worker_id=w_id))
        db.commit()

    db.refresh(task)
    return format_task(task, db)


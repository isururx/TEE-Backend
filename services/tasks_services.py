from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.task import Task, TaskWorker
from app.db.models.worker import Worker
from app.schemas.task import TaskCreate, TaskMetricsOut, TaskStatusUpdate
from app.services.sms_service import send_sms


def get_task_metrics_service(db: Session):
    pending_count = (
        db.query(func.count(Task.id))
        .filter(Task.status.in_(["QUEUED", "PENDING"]))
        .scalar()
    )

    critical_count = (
        db.query(func.count(Task.id))
        .filter(Task.priority == "CRITICAL", Task.status != "ARCHIVED")
        .scalar()
    )

    total_active = (
        db.query(func.count(Task.id))
        .filter(Task.status != "ARCHIVED")
        .scalar()
    ) or 1

    priority_counts = (
        db.query(Task.priority, func.count(Task.id))
        .filter(Task.status != "ARCHIVED")
        .group_by(Task.priority)
        .all()
    )

    labor_allocation = {
        priority: round((count / total_active) * 100, 1)
        for priority, count in priority_counts
    }

    return TaskMetricsOut(
        pending_count=pending_count,
        critical_count=critical_count,
        labor_allocation=labor_allocation,
    )


def get_my_tasks_service(db: Session, worker_id: int):
    assigned_task_ids = (
        db.query(TaskWorker.task_id)
        .filter(TaskWorker.worker_id == worker_id)
        .subquery()
    )

    tasks = (
        db.query(Task)
        .filter(Task.id.in_(assigned_task_ids))
        .order_by(Task.created_at.desc())
        .all()
    )
    return [_build_task_response(db, task) for task in tasks]


def list_tasks_service(
    db: Session,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)

    if search:
        query = query.filter(Task.description.ilike(f"%{search}%"))

    tasks = query.order_by(Task.created_at.desc()).all()
    return [_build_task_response(db, task) for task in tasks]


async def create_task_service(db: Session, data: TaskCreate):
    task = Task(
        description=data.description,
        block_id=data.block_id,
        priority=data.priority,
        status="QUEUED",
        deadline=data.deadline,
    )
    db.add(task)
    db.flush()

    for worker_id in data.worker_ids:
        db.add(TaskWorker(task_id=task.id, worker_id=worker_id))

    db.commit()
    db.refresh(task)

    await _send_task_assignment_sms(db=db, task=task, data=data)

    return _build_task_response(db, task)


def update_task_status_service(
    db: Session,
    task_id: int,
    data: TaskStatusUpdate,
):
    task = _get_task_or_404(db, task_id)
    task.status = data.status
    db.commit()
    db.refresh(task)
    return _build_task_response(db, task)


def get_task_service(db: Session, task_id: int):
    task = _get_task_or_404(db, task_id)
    return _build_task_response(db, task)


async def _send_task_assignment_sms(
    db: Session,
    task: Task,
    data: TaskCreate,
):
    for worker_id in data.worker_ids:
        worker = db.query(Worker).filter(Worker.id == worker_id).first()
        if worker and worker.phone_num:
            try:
                message = (
                    f"TEE Task #{task.id}: You have been assigned "
                    f"{data.description or 'a field task'}. Priority: {data.priority}."
                )
                await send_sms(recipient=worker.phone_num, message=message)
            except Exception as exc:
                print(f"[SMS] Failed for worker {worker_id}: {repr(exc)}")


def _get_task_or_404(db: Session, task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


def _build_task_response(db: Session, task: Task):
    assigned_workers = (
        db.query(Worker)
        .join(TaskWorker, TaskWorker.worker_id == Worker.id)
        .filter(TaskWorker.task_id == task.id)
        .order_by(Worker.name)
        .all()
    )

    return {
        "id": task.id,
        "description": task.description,
        "block_id": task.block_id,
        "assigned_worker_ids": [worker.id for worker in assigned_workers],
        "assigned_worker_names": [worker.name for worker in assigned_workers],
        "priority": task.priority,
        "status": task.status,
        "deadline": task.deadline,
        "created_by": task.created_by,
        "created_at": task.created_at,
    }

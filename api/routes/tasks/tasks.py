from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.task import Task, TaskWorker
from app.db.models.user import User
from app.schemas.task import TaskCreate, TaskMetricsOut, TaskOut, TaskStatusUpdate
from app.services.sms_service import send_sms

router = APIRouter()


# ── NOTE: /metrics and /my-tasks MUST be declared before /{task_id} ──────────
# FastAPI matches routes top-to-bottom; if /{task_id} came first it would
# capture the literal strings "metrics" and "my-tasks" as the path param.


# ── GET /api/tasks/metrics ───────────────────────────────────────────────────

@router.get("/metrics", response_model=TaskMetricsOut)
def get_task_metrics(db: Session = Depends(get_db)):
    """Aggregate task KPIs for the top-of-screen metric cards."""

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

    # Labor allocation: percentage of active tasks per task_type
    total_active = (
        db.query(func.count(Task.id))
        .filter(Task.status != "ARCHIVED")
        .scalar()
    ) or 1  # avoid division by zero

    type_counts = (
        db.query(Task.task_type, func.count(Task.id))
        .filter(Task.status != "ARCHIVED")
        .group_by(Task.task_type)
        .all()
    )

    labor_allocation = {
        task_type: round((count / total_active) * 100, 1)
        for task_type, count in type_counts
    }

    return TaskMetricsOut(
        pending_count=pending_count,
        critical_count=critical_count,
        labor_allocation=labor_allocation,
    )


# ── GET /api/tasks/my-tasks ──────────────────────────────────────────────────

@router.get("/my-tasks", response_model=List[TaskOut])
def get_my_tasks(
    worker_id: int = Query(..., description="Worker's user ID"),
    db: Session = Depends(get_db),
):
    """
    Return tasks assigned to a specific worker.
    TODO: replace `worker_id` query param with JWT auth dependency
    once token issuance is added to verify-2fa.
    """
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
    return tasks


# ── GET /api/tasks ───────────────────────────────────────────────────────────

@router.get("", response_model=List[TaskOut])
def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search task_type or description"),
    db: Session = Depends(get_db),
):
    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)

    if search:
        query = query.filter(
            Task.task_type.ilike(f"%{search}%")
            | Task.description.ilike(f"%{search}%")
        )

    return query.order_by(Task.created_at.desc()).all()


# ── POST /api/tasks ──────────────────────────────────────────────────────────

@router.post("", response_model=TaskOut, status_code=201)
async def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a task, assign workers, and send SMS notifications.
    SMS failure does NOT roll back the task — it is logged and swallowed.
    """
    task = Task(
        task_type=data.task_type,
        description=data.description,
        block_id=data.block_id,
        priority=data.priority,
        status="QUEUED",
        deadline=data.deadline,
    )
    db.add(task)
    db.flush()  # Populate task.id before assigning task_code

    # Generate readable task code from auto-incremented PK
    task.task_code = f"T-{task.id:04d}"

    # Insert TaskWorker mapping rows
    for worker_id in data.worker_ids:
        db.add(TaskWorker(task_id=task.id, worker_id=worker_id))

    db.commit()
    db.refresh(task)

    # ── SMS notifications ────────────────────────────────────────────────────
    for worker_id in data.worker_ids:
        worker = db.query(User).filter(User.id == worker_id).first()
        if worker and worker.phone_num:
            try:
                msg = (
                    f"TEE Task [{task.task_code}]: You have been assigned "
                    f"{data.task_type}. Priority: {data.priority}."
                )
                await send_sms(recipient=worker.phone_num, message=msg)
            except Exception as exc:
                # Non-fatal — task is already committed
                print(f"[SMS] Failed for worker {worker_id}: {repr(exc)}")

    return task


# ── PATCH /api/tasks/{task_id}/status ────────────────────────────────────────

@router.patch("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    db: Session = Depends(get_db),
):
    task = _get_task_or_404(task_id, db)
    task.status = data.status
    db.commit()
    db.refresh(task)
    return task


# ── GET /api/tasks/{task_id} ─────────────────────────────────────────────────

@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return _get_task_or_404(task_id, db)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_task_or_404(task_id: int, db: Session) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task

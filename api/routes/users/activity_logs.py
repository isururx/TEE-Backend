from datetime import date, datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.activity_log import ActivityLog
from app.db.models.user import User

router = APIRouter()

AVATAR_COLORS = ["#16A34A", "#7C3AED", "#1B5E20", "#0EA5E9", "#F59E0B", "#DC2626"]


def _infer_action_type(action: str) -> str:
    lower = (action or "").lower()
    if "delete" in lower or "remove" in lower:
        return "delete"
    if "create" in lower or "add" in lower or "register" in lower:
        return "create"
    if "approve" in lower:
        return "approve"
    if "login" in lower:
        return "login"
    if "logout" in lower:
        return "logout"
    if "export" in lower:
        return "export"
    return "update"


def _initials(name: str) -> str:
    parts = [p for p in (name or "SY").split() if p]
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return (name or "SY")[:2].upper()


@router.get("")
def get_activity_logs(db: Session = Depends(get_db)):
    """Return activity logs and live summary statistics from the database."""
    total_activities = db.query(func.count(ActivityLog.id)).scalar() or 0
    today_start = datetime.combine(date.today(), time.min)
    today_activities = (
        db.query(func.count(ActivityLog.id))
        .filter(ActivityLog.timestamp >= today_start)
        .scalar()
        or 0
    )
    active_users = (
        db.query(func.count(User.id))
        .filter(User.is_active == True)
        .scalar()
        or 0
    )
    failed_activities = (
        db.query(func.count(ActivityLog.id))
        .filter(ActivityLog.action.ilike("%fail%"))
        .scalar()
        or 0
    )

    rows = (
        db.query(ActivityLog)
        .order_by(ActivityLog.timestamp.desc())
        .limit(200)
        .all()
    )

    logs = []
    for idx, row in enumerate(rows):
        user_name = row.user.name if row.user else "System"
        user_email = row.user.email if row.user else "system@tee.lk"
        user_role = row.user.role if row.user else "Admin"
        is_failed = "fail" in (row.action or "").lower()
        logs.append(
            {
                "id": row.id,
                "timestamp": row.timestamp.strftime("%d %b %Y %I:%M:%S %p") if row.timestamp else "",
                "user": user_name,
                "email": user_email,
                "initials": _initials(user_name),
                "avatarBg": AVATAR_COLORS[idx % len(AVATAR_COLORS)],
                "role": user_role,
                "action": row.action,
                "actionType": _infer_action_type(row.action),
                "module": "User Management" if "role" in (row.action or "").lower() or "profile" in (row.action or "").lower() or "status" in (row.action or "").lower() else "System",
                "description": row.details or row.action,
                "status": "Failed" if is_failed else "Success",
                "extra": row.details or "",
            }
        )

    return {
        "stats": {
            "total_activities": total_activities,
            "today_activities": today_activities,
            "active_users": active_users,
            "failed_activities": failed_activities,
        },
        "logs": logs,
    }

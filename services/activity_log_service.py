from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models.activity_log import ActivityLog


def log_system_event(
    db: Session,
    action: str,
    details: Optional[str] = None,
    user_id: Optional[int] = None,
    commit: bool = True,
) -> ActivityLog:
    """MT-15: Central helper for writing system audit events.

    System-level twin of ``log_block_event`` (MT-14): writes to
    ``activity_logs`` instead of ``block_activity_logs``. Used by
    cross-entity hooks that are not tied to a plantation block —
    user role updates/approvals (MT-23) and supplier
    creation/deletion (MT-24).

    Args:
        db: Active SQLAlchemy session.
        action: Short action label, e.g. ``"User Role Updated"``,
            ``"Supplier Deleted"``. Required, non-empty.
        details: Longer human-readable description, e.g.
            ``"Changed Nimal Perera role: Worker -> Supervisor"``.
            Nullable.
        user_id: Actor's ``users.id`` (FK, nullable — system
            actions may have no user).
        commit: When True (default) the row is committed immediately.
            Pass ``commit=False`` when the caller will commit the
            surrounding transaction itself (avoids partial commits).

    Returns:
        The persisted (refreshed when committed) ``ActivityLog``.
    """
    if not action or not action.strip():
        raise HTTPException(status_code=400, detail="Action is required")

    log = ActivityLog(
        user_id=user_id,
        action=action.strip(),
        details=details.strip() if details and details.strip() else details,
    )
    db.add(log)
    if commit:
        db.commit()
        db.refresh(log)
    else:
        db.flush()
    return log

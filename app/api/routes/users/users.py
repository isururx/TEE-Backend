from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.dependencies.auth import get_current_user
from app.db.database import get_db
from app.db.models.activity_log import ActivityLog
from app.db.models.user import User
from app.db.models.worker import Worker
from app.schemas.user import UserResponse

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)):
    if 'admin' not in (current_user.role or '').lower():
        raise HTTPException(status_code=403, detail='Administrator access required')
    return current_user


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone_num: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    role: Optional[str] = None


class UserRoleUpdate(BaseModel):
    role: str


class UserStatusUpdate(BaseModel):
    is_active: bool


def _serialize_user_profile(user: User, worker: Optional[Worker]) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone_num": user.phone_num or (str(worker.phone_num) if worker and worker.phone_num else ""),
        "role": user.role,
        "is_active": user.is_active,
        "status": "Active" if user.is_active else "Deactivated",
        "address": worker.address if worker else "",
        "employeeId": f"W-{user.id}" if (user.role or "").lower() == "worker" else f"USR-{user.id:03d}",
        "assigned_block": worker.assigned_block if worker else None,
    }


def _log_activity(db: Session, user_id: Optional[int], action: str, details: str):
    db.add(ActivityLog(user_id=user_id, action=action, details=details))


@router.get("", response_model=List[UserResponse], dependencies=[Depends(require_admin)])
def get_users(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role.ilike(role))

    return query.order_by(User.name.asc()).all()


@router.get("/{user_id}")
def get_user_profile(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id != current_user.id and "admin" not in (current_user.role or "").lower():
        raise HTTPException(status_code=403, detail="You can only view your own profile")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    worker = db.query(Worker).filter(Worker.id == user_id).first()
    return _serialize_user_profile(user, worker)


@router.put("/{user_id}")
def update_user_profile(user_id: int, data: UserProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id != current_user.id and "admin" not in (current_user.role or "").lower():
        raise HTTPException(status_code=403, detail="You can only update your own profile")
    if data.role is not None and "admin" not in (current_user.role or "").lower():
        raise HTTPException(status_code=403, detail="Only administrators can change roles")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.name is not None and data.name.strip():
        user.name = data.name.strip()
    if data.email is not None and data.email.strip():
        user.email = data.email.strip()
    phone_val = data.phone_num if data.phone_num is not None else data.phone
    if phone_val is not None:
        user.phone_num = phone_val.strip()
    if data.role is not None and data.role.strip():
        user.role = data.role.strip()

    worker = db.query(Worker).filter(Worker.id == user_id).first()
    if worker:
        if data.name is not None and data.name.strip():
            worker.name = data.name.strip()
        if data.email is not None and data.email.strip():
            worker.email = data.email.strip()
        if data.address is not None:
            worker.address = data.address.strip()
        if phone_val is not None:
            digits = "".join(ch for ch in phone_val if ch.isdigit())
            if digits:
                worker.phone_num = int(digits)

    _log_activity(db, user.id, "Profile Updated", f"Updated profile details for {user.name}")
    db.commit()
    db.refresh(user)
    if worker:
        db.refresh(worker)
    return _serialize_user_profile(user, worker)


@router.patch("/{user_id}/role", dependencies=[Depends(require_admin)])
def update_user_role(user_id: int, data: UserRoleUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    old_role = user.role
    user.role = data.role.strip()
    _log_activity(db, user.id, "Role Changed", f"Changed {user.name} role: {old_role} -> {user.role}")
    db.commit()
    db.refresh(user)
    worker = db.query(Worker).filter(Worker.id == user_id).first()
    return _serialize_user_profile(user, worker)


@router.patch("/{user_id}/status", dependencies=[Depends(require_admin)])
def update_user_status(user_id: int, data: UserStatusUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = data.is_active
    status_label = "Active" if user.is_active else "Deactivated"
    _log_activity(db, user.id, "Status Changed", f"Set {user.name} status to {status_label}")
    db.commit()
    db.refresh(user)
    worker = db.query(Worker).filter(Worker.id == user_id).first()
    return _serialize_user_profile(user, worker)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.db.models.user import User
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("", response_model=List[UserResponse])
def get_users(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role.ilike(role))

    return query.order_by(User.name.asc()).all()

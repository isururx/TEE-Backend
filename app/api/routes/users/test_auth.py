from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.db.models.user import User


router = APIRouter()


@router.get("/protected")
async def protected_endpoint(current_user: User = Depends(get_current_user)):
    return {
        "message": "You are authenticated",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role
        }
    }
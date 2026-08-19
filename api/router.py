from fastapi import APIRouter

from app.api.routes.detection.detection import router as detection_router
from app.api.routes.users.auth import router as auth_router


api_router = APIRouter()


api_router.include_router(
    detection_router,
    prefix="/detection",
    tags=["Disease Detection"]
)

api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)
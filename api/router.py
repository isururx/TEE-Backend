from fastapi import APIRouter

from app.api.routes.detection.detection import router as detection_router


api_router = APIRouter()

api_router.include_router(
    detection_router,
    prefix="/detection",
    tags=["Disease Detection"]
)
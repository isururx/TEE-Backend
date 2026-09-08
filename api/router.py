from fastapi import APIRouter

from app.api.routes.detection.detection import router as detection_router
from app.api.routes.users.auth import router as auth_router
from app.api.routes.users.users import router as users_router
from app.api.routes.blocks.blocks import router as blocks_router
from app.api.routes.workers.workers import router as workers_router
from app.api.routes.tasks.tasks import router as tasks_router
from app.api.routes.attendance.attendance import router as attendance_router
from app.api.routes.users.test_auth import router as test_auth_router


api_router = APIRouter()

api_router.include_router(
    test_auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

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

api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Users"]
)

api_router.include_router(
    blocks_router,
    prefix="/blocks",
    tags=["Plantation Blocks"]
)

api_router.include_router(
    workers_router,
    prefix="/workers",
    tags=["Workers"]
)

api_router.include_router(
    tasks_router,
    prefix="/tasks",
    tags=["Tasks"]
)

api_router.include_router(
    attendance_router,
    prefix="/attendance",
    tags=["Attendance"]
)

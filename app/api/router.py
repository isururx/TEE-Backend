from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user

from app.api.routes.detection.detection import router as detection_router
from app.api.routes.users.auth import router as auth_router
from app.api.routes.users.users import router as users_router
from app.api.routes.blocks.blocks import router as blocks_router
from app.api.routes.workers.workers import router as workers_router
from app.api.routes.tasks.tasks import router as tasks_router
from app.api.routes.attendance.attendance import router as attendance_router
from app.api.routes.users.test_auth import router as test_auth_router
from app.api.routes.dashboard.dashboard import router as dashboard_router
from app.api.routes.users.activity_logs import router as activity_logs_router


api_router = APIRouter()

api_router.include_router(
    test_auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    detection_router,
    prefix="/detection",
    tags=["Disease Detection"],
    dependencies=[Depends(get_current_user)]
)

api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    users_router,
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)]
)

api_router.include_router(
    blocks_router,
    prefix="/blocks",
    tags=["Plantation Blocks"],
    dependencies=[Depends(get_current_user)]
)

api_router.include_router(
    workers_router,
    prefix="/workers",
    tags=["Workers"],
    dependencies=[Depends(get_current_user)]
)

api_router.include_router(
    tasks_router,
    prefix="/tasks",
    tags=["Tasks"],
    dependencies=[Depends(get_current_user)]
)

api_router.include_router(
    attendance_router,
    prefix="/attendance",
    tags=["Attendance"],
    dependencies=[Depends(get_current_user)]
)

api_router.include_router(
    dashboard_router,
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)]
)

api_router.include_router(
    activity_logs_router,
    prefix="/activity-logs",
    tags=["Activity Logs"],
    dependencies=[Depends(get_current_user)]
)

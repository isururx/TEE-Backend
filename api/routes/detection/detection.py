from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.database import get_db
from app.db.models.plantation_block import PlantationBlock
from app.db.models.user import User
from app.db.models.worker import Worker
from app.services.detection_service import run_detection

router = APIRouter()

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
UNASSIGNED_DETECTION_ROLES = {"admin", "manager", "estate manager"}


def _authorize_unassigned_detection(current_user: User) -> None:
    """Only estate-level administrators/managers may save an unassigned event."""
    if not getattr(current_user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    role = (current_user.role or "").strip().lower()
    if role not in UNASSIGNED_DETECTION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an administrator or estate manager may submit an unassigned detection.",
        )


def _authorize_block_access(db: Session, current_user: User, block: PlantationBlock) -> None:
    """Enforce role-based plantation block access using existing DB relationships."""
    if not getattr(current_user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    role = (current_user.role or "").strip().lower()

    if role in UNASSIGNED_DETECTION_ROLES:
        return

    if role == "supervisor":
        if block.supervisor_id == current_user.id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to submit detections for this plantation block.",
        )

    if role in {"worker", "field worker"}:
        worker = db.query(Worker).filter(Worker.id == current_user.id).first()
        if worker and worker.assigned_block == block.id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to submit detections for this plantation block.",
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Your role is not authorized to submit disease detections.",
    )


def _validate_uploaded_image(image: UploadFile) -> None:
    """Validate uploaded image MIME type and filename extension."""
    content_type = (image.content_type or "").strip().lower()
    if not content_type or not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a valid image.",
        )

    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image format. Please upload a JPG, PNG, or WEBP image.",
        )

    if image.filename:
        ext = Path(image.filename).suffix.lower()
        if ext and ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported image file extension. Allowed formats: .jpg, .jpeg, .png, .webp.",
            )


@router.post("/detect")
async def detect_disease(
    image: UploadFile = File(...),
    block_id: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Validate uploaded file
    _validate_uploaded_image(image)

    # 2. Validate the selected block, or explicitly authorize an unassigned event
    block = None
    if block_id is None:
        _authorize_unassigned_detection(current_user)
    else:
        block = (
            db.query(PlantationBlock)
            .filter(PlantationBlock.id == block_id)
            .first()
        )

        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantation block not found.",
            )

        # 3. Enforce role-based authorization for the selected block
        _authorize_block_access(db, current_user, block)

    # 4. Run detection using the authenticated user and validated block
    return await run_detection(
        image=image,
        user_id=current_user.id,
        block_id=block.id if block else None,
        db=db,
    )

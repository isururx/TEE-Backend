
# api/routes/detection/detection.py

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from db.database import get_db
from db.models.plantation_block import PlantationBlock

from services.detection_service import run_detection

# IMPORTANT:
# Replace this import with the actual location of get_current_user
# in your existing backend.
from core.security import get_current_user

router = APIRouter()


@router.post("/detect")
async def detect_disease(
    image: UploadFile = File(...),
    block_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # 1. Validate uploaded file
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid image."
        )

    # 2. Verify that the selected block exists
    block = (
        db.query(PlantationBlock)
        .filter(PlantationBlock.id == block_id)
        .first()
    )

    if not block:
        raise HTTPException(
            status_code=404,
            detail="Plantation block not found."
        )

    # 3. Run detection using the authenticated user and selected block
    return await run_detection(
    image=image,
    user_id=current_user.id,
    block_id=block.id,
)
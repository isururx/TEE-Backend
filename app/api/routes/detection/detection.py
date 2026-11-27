from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.detection_service import run_detection

router = APIRouter()

# Temporary test values
TEST_USER_ID = 3
TEST_BLOCK_ID = 1

@router.post("/detect")
async def detect_disease(
    image: UploadFile = File(...)
    #user_id: int = Form(...),
    #block_id: int | None = Form(None)
):
    try:
        return await run_detection(
            image=image,
            user_id=TEST_USER_ID,
            block_id=TEST_BLOCK_ID
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
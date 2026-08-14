from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.detection_service import run_detection

router = APIRouter()


@router.post("/detect")
async def detect_disease(image: UploadFile = File(...)):
    try:
        return await run_detection(image)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
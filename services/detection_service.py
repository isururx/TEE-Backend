from datetime import datetime
import logging
from pathlib import Path
from typing import Optional
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models.detection import DiseaseDetection
from app.db.models.disease import Disease
from app.ml.model import predict_image
from app.ml.preprocess import preprocess_image

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads/detections")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _resolve_safe_extension(image: UploadFile) -> str:
    """Return a whitelisted file extension without trusting raw filename paths."""
    if image.filename:
        ext = Path(image.filename).suffix.lower()
        if ext in ALLOWED_EXTENSIONS:
            return ext

    content_type = (image.content_type or "").strip().lower()
    return CONTENT_TYPE_EXTENSIONS.get(content_type, ".jpg")


async def run_detection(
    image: UploadFile,
    user_id: int,
    block_id: int | None = None,
    db: Optional[Session] = None,
):
    if block_id is None:
        raise HTTPException(
            status_code=422,
            detail="Plantation block ID is required.",
        )

    # -----------------------------
    # 1. Read & validate uploaded image
    # -----------------------------
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image file is empty.",
        )

    # -----------------------------
    # 2. Run preprocessing
    # -----------------------------
    try:
        processed_image = preprocess_image(image_bytes)
    except Exception:
        logger.warning("Invalid or unreadable image uploaded for detection")
        raise HTTPException(
            status_code=400,
            detail="Invalid or corrupted image file.",
        )

    # -----------------------------
    # 3. Run AI prediction
    # -----------------------------
    try:
        disease_name, confidence = predict_image(processed_image)
    except Exception:
        logger.exception("CNN disease prediction failed")
        raise HTTPException(
            status_code=500,
            detail="Disease prediction failed. Please try again.",
        )

    # -----------------------------
    # 4. Validate disease & save detection record
    # -----------------------------
    session = db if db is not None else SessionLocal()
    owns_session = db is None
    saved_image_path: Optional[Path] = None

    try:
        disease = (
            session.query(Disease)
            .filter(Disease.name == disease_name)
            .first()
        )

        if not disease:
            logger.error("Predicted disease label %r not found in database", disease_name)
            raise HTTPException(
                status_code=422,
                detail=f"Predicted disease '{disease_name}' is not registered in the database.",
            )

        file_extension = _resolve_safe_extension(image)
        filename = f"{uuid.uuid4()}{file_extension}"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        image_path = UPLOAD_DIR / filename

        with open(image_path, "wb") as file:
            file.write(image_bytes)
        saved_image_path = image_path

        detection = DiseaseDetection(
            disease_id=disease.id,
            user_id=user_id,
            block_id=block_id,
            image_path=str(image_path),
            confidence_score=float(confidence),
            timestamp=datetime.utcnow(),
        )

        session.add(detection)
        session.commit()
        session.refresh(detection)
        detection_id = detection.id

    except HTTPException:
        session.rollback()
        raise
    except Exception:
        session.rollback()
        if saved_image_path and saved_image_path.exists():
            try:
                saved_image_path.unlink()
            except OSError:
                logger.warning("Failed to clean up orphaned detection image file")
        logger.exception("Failed to persist disease detection record")
        raise HTTPException(
            status_code=500,
            detail="Failed to save detection record.",
        )
    finally:
        if owns_session:
            session.close()

    # -----------------------------
    # 5. Existing response
    # -----------------------------
    is_healthy = disease_name.lower() == "healthy leaf"

    return {
        "detection_id": detection_id,
        "is_healthy": is_healthy,
        "disease_name": disease_name,
        "confidence": float(confidence),
        "severity": get_severity(disease_name, confidence),
        "description": get_description(disease_name),
        "recommendations": get_recommendations(disease_name),
    }


def get_severity(disease_name, confidence):

    if disease_name.lower() == "healthy leaf":
        return "Low"

    if confidence >= 0.85:
        return "High"

    if confidence >= 0.60:
        return "Moderate"

    return "Low"


def get_description(disease_name):

    descriptions = {

        "Brown Blight":
            "Signs consistent with brown blight were detected.",

        "Gray Blight":
            "Signs consistent with gray blight were detected.",

        "Green mirid bug":
            "Signs consistent with green mirid bug damage were detected.",

        "Healthy leaf":
            "No visible signs of disease were detected.",

        "Helopeltis":
            "Signs consistent with Helopeltis damage were detected.",

        "Red spider":
            "Signs consistent with red spider damage were detected.",

        "Tea algal leaf spot":
            "Signs consistent with tea algal leaf spot were detected."
    }

    return descriptions.get(
        disease_name,
        "The model detected a condition requiring further inspection."
    )


def get_recommendations(disease_name):

    recommendations = {

        "Healthy leaf": [
            "Continue regular monitoring.",
            "Maintain current estate management practices."
        ],

        "Brown Blight": [
            "Remove severely affected leaves where appropriate.",
            "Follow the recommended treatment according to estate guidelines.",
            "Monitor surrounding plants for further infection."
        ],

        "Gray Blight": [
            "Remove severely affected leaves where appropriate.",
            "Follow the recommended treatment according to estate guidelines.",
            "Monitor the affected plantation block."
        ],

        "Green mirid bug": [
            "Inspect surrounding tea plants for further infestation.",
            "Follow the estate's recommended pest management procedure.",
            "Continue monitoring the affected plantation block."
        ],

        "Helopeltis": [
            "Inspect surrounding plants for further infestation.",
            "Follow the estate's recommended pest management procedure.",
            "Monitor the affected plantation block."
        ],

        "Red spider": [
            "Inspect affected leaves and surrounding plants.",
            "Follow the estate's recommended pest management procedure.",
            "Continue monitoring for further spread."
        ],

        "Tea algal leaf spot": [
            "Remove severely affected leaves where appropriate.",
            "Follow the recommended treatment according to estate guidelines.",
            "Monitor the affected plantation block."
        ]
    }

    return recommendations.get(disease_name, [])

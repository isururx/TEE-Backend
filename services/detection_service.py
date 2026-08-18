from datetime import datetime
from pathlib import Path
import uuid

from fastapi import UploadFile

from app.ml.model import predict_image
from app.ml.preprocess import preprocess_image

from app.db.database import SessionLocal
from app.db.models.disease import Disease
from app.db.models.detection import DiseaseDetection


UPLOAD_DIR = Path("uploads/detections")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def run_detection(
    image: UploadFile,
    user_id: int,
    block_id: int | None = None
):

    # -----------------------------
    # 1. Read uploaded image
    # -----------------------------

    image_bytes = await image.read()

    # -----------------------------
    # 2. Run preprocessing
    # -----------------------------

    processed_image = preprocess_image(image_bytes)

    # -----------------------------
    # 3. Run AI prediction
    # -----------------------------

    disease_name, confidence = predict_image(processed_image)

    # -----------------------------
    # 4. Save image
    # -----------------------------

    file_extension = Path(image.filename).suffix

    filename = f"{uuid.uuid4()}{file_extension}"

    image_path = UPLOAD_DIR / filename

    with open(image_path, "wb") as file:
        file.write(image_bytes)

    # -----------------------------
    # 5. Find disease in database
    # -----------------------------

    db = SessionLocal()

    try:

        disease = (
            db.query(Disease)
            .filter(Disease.name == disease_name)
            .first()
        )

        if not disease:
            raise Exception(
                f"Disease '{disease_name}' was not found in database"
            )

        # -----------------------------
        # 6. Create detection record
        # -----------------------------

        detection = DiseaseDetection(
            disease_id=disease.id,
            user_id=user_id,
            block_id=block_id,
            image_path=str(image_path),
            confidence_score=confidence,
            timestamp=datetime.utcnow()
        )

        db.add(detection)

        db.commit()

        db.refresh(detection)

        detection_id = detection.id

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    # -----------------------------
    # 7. Existing response
    # -----------------------------

    is_healthy = disease_name.lower() == "healthy leaf"

    return {
        "detection_id": detection_id,
        "is_healthy": is_healthy,
        "disease_name": disease_name,
        "confidence": confidence,
        "severity": get_severity(disease_name, confidence),
        "description": get_description(disease_name),
        "recommendations": get_recommendations(disease_name)
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
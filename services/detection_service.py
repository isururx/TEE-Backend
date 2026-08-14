from fastapi import UploadFile

from app.ml.model import predict_image
from app.ml.preprocess import preprocess_image


async def run_detection(image: UploadFile):

    image_bytes = await image.read()

    processed_image = preprocess_image(image_bytes)

    disease_name, confidence = predict_image(processed_image)

    is_healthy = disease_name.lower() == "healthy leaf"

    return {
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
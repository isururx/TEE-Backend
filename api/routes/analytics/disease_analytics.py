from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.database import get_db
from app.db.models.disease import Disease
from app.db.models.plantation_block import PlantationBlock
from app.db.models.user import User
from app.schemas.analytics import (
    BlockDiseaseSummaryResponse,
    DiseaseDistributionResponse,
    DiseaseFrequencyByBlockResponse,
)
from app.services.analytics.disease_analytics_service import (
    get_disease_analytics_summary,
)

router = APIRouter()

ESTATE_ANALYTICS_ROLES = {"admin", "manager", "estate manager"}
SUPERVISOR_ROLE = "supervisor"


def _authorize_analytics_access(
    db: Session,
    current_user: User,
    block_id: Optional[int],
) -> None:
    """Allow estate-wide roles; supervisors may view only their own block."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive users cannot access disease analytics.",
        )

    role = (current_user.role or "").strip().lower()
    if role in ESTATE_ANALYTICS_ROLES:
        return

    if role == SUPERVISOR_ROLE:
        if block_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Supervisors must select their assigned plantation block.",
            )

        block = (
            db.query(PlantationBlock)
            .filter(PlantationBlock.id == block_id)
            .first()
        )
        if block is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantation block not found.",
            )
        if block.supervisor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view analytics for this block.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Your role is not authorized to access disease analytics.",
    )


def _validate_filter_references(
    db: Session,
    block_id: Optional[int],
    disease_id: Optional[int],
) -> None:
    if block_id is not None:
        block = (
            db.query(PlantationBlock)
            .filter(PlantationBlock.id == block_id)
            .first()
        )
        if block is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plantation block not found.",
            )

    if disease_id is not None:
        disease = db.query(Disease).filter(Disease.id == disease_id).first()
        if disease is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Disease not found.",
            )


def _get_analytics(
    db: Session,
    current_user: User,
    start_date: Optional[date],
    end_date: Optional[date],
    block_id: Optional[int],
    disease_id: Optional[int],
) -> dict:
    _authorize_analytics_access(db, current_user, block_id)
    _validate_filter_references(db, block_id, disease_id)

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must be on or before end_date.",
        )

    return get_disease_analytics_summary(
        db=db,
        start_date=start_date,
        end_date=end_date,
        block_id=block_id,
        disease_id=disease_id,
    )


@router.get(
    "/disease-frequency-by-block",
    response_model=DiseaseFrequencyByBlockResponse,
    summary="Get disease frequency grouped by plantation block",
)
def get_disease_frequency_by_block(
    start_date: Optional[date] = Query(None, description="Inclusive start date (UTC)."),
    end_date: Optional[date] = Query(None, description="Inclusive end date (UTC)."),
    block_id: Optional[int] = Query(None, ge=1),
    disease_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return total detection counts and disease frequency for each block."""
    result = _get_analytics(
        db, current_user, start_date, end_date, block_id, disease_id
    )
    return {
        "period": result["period"],
        "summary": result["summary"],
        "blocks": [
            {
                "block_id": block["block_id"],
                "block_name": block["block_name"],
                "total_detections": block["total_detections"],
                "diseases": block["diseases"],
            }
            for block in result["blocks"]
        ],
        "filters": result["filters"],
    }


@router.get(
    "/disease-distribution",
    response_model=DiseaseDistributionResponse,
    summary="Get overall disease distribution",
)
def get_disease_distribution(
    start_date: Optional[date] = Query(None, description="Inclusive start date (UTC)."),
    end_date: Optional[date] = Query(None, description="Inclusive end date (UTC)."),
    block_id: Optional[int] = Query(None, ge=1),
    disease_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return disease event frequencies across the selected scope."""
    result = _get_analytics(
        db, current_user, start_date, end_date, block_id, disease_id
    )
    return {
        "period": result["period"],
        "total_detections": result["summary"]["total_detections"],
        "diseased_detections": result["summary"]["diseased_detections"],
        "disease_distribution": result["disease_distribution"],
        "filters": result["filters"],
    }


@router.get(
    "/block-disease-summary",
    response_model=BlockDiseaseSummaryResponse,
    summary="Get disease analytics for one plantation block",
)
def get_block_disease_summary(
    block_id: int = Query(..., ge=1),
    start_date: Optional[date] = Query(None, description="Inclusive start date (UTC)."),
    end_date: Optional[date] = Query(None, description="Inclusive end date (UTC)."),
    disease_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a detailed disease summary for one selected block."""
    result = _get_analytics(
        db, current_user, start_date, end_date, block_id, disease_id
    )
    block = next(
        (item for item in result["blocks"] if item["block_id"] == block_id),
        None,
    )
    if block is None:
        # A valid block with no detections is still returned by the service.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantation block not found.",
        )

    return {
        "period": result["period"],
        "summary": result["summary"],
        "block": block,
        "filters": result["filters"],
    }

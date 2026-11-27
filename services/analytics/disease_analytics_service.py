"""Database-backed disease analytics for Module 04, Feature 01.

Detection timestamps are stored as naive UTC datetimes by the existing
detection service. Date filters therefore use UTC calendar-day boundaries:
start_date is inclusive and end_date is inclusive (implemented as the
exclusive midnight boundary of the following day).
"""

from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db.models.detection import DiseaseDetection
from app.db.models.disease import Disease
from app.db.models.plantation_block import PlantationBlock


HEALTHY_DISEASE_LABEL = "healthy leaf"


def _validate_date_range(
    start_date: Optional[date],
    end_date: Optional[date],
) -> None:
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")


def _apply_detection_filters(
    query,
    start_date: Optional[date],
    end_date: Optional[date],
    block_id: Optional[int],
    disease_id: Optional[int],
):
    """Apply shared filters to a query that already joins DiseaseDetection."""
    if start_date:
        start_boundary = datetime.combine(start_date, time.min)
        query = query.filter(DiseaseDetection.timestamp >= start_boundary)

    if end_date:
        end_exclusive = datetime.combine(end_date + timedelta(days=1), time.min)
        query = query.filter(DiseaseDetection.timestamp < end_exclusive)

    if block_id is not None:
        query = query.filter(DiseaseDetection.block_id == block_id)

    if disease_id is not None:
        query = query.filter(DiseaseDetection.disease_id == disease_id)

    return query


def get_disease_analytics_summary(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    block_id: Optional[int] = None,
    disease_id: Optional[int] = None,
) -> dict:
    """Return disease analytics aggregated in the database.

    The response includes every registered block (including blocks with no
    detections), separates healthy and unassigned events, and excludes the
    healthy-leaf class from disease-frequency rankings.
    """
    _validate_date_range(start_date, end_date)

    base_query = db.query(DiseaseDetection).join(
        Disease, Disease.id == DiseaseDetection.disease_id
    )
    base_query = _apply_detection_filters(
        base_query, start_date, end_date, block_id, disease_id
    )

    summary_row = (
        db.query(
            func.count(DiseaseDetection.id),
            func.coalesce(
                func.sum(
                    case(
                        (
                            func.lower(func.trim(Disease.name))
                            == HEALTHY_DISEASE_LABEL,
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((DiseaseDetection.block_id.is_(None), 1), else_=0)
                ),
                0,
            ),
        )
        .join(Disease, Disease.id == DiseaseDetection.disease_id)
    )
    summary_row = _apply_detection_filters(
        summary_row, start_date, end_date, block_id, disease_id
    ).one()

    total_detections = int(summary_row[0] or 0)
    healthy_detections = int(summary_row[1] or 0)
    unassigned_detections = int(summary_row[2] or 0)

    block_totals_rows = (
        db.query(
            DiseaseDetection.block_id.label("block_id"),
            func.count(DiseaseDetection.id).label("total_detections"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            func.lower(func.trim(Disease.name))
                            == HEALTHY_DISEASE_LABEL,
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("healthy_detections"),
        )
        .join(Disease, Disease.id == DiseaseDetection.disease_id)
        .filter(DiseaseDetection.block_id.isnot(None))
    )
    block_totals_rows = _apply_detection_filters(
        block_totals_rows, start_date, end_date, block_id, disease_id
    ).group_by(DiseaseDetection.block_id).all()

    block_totals = {
        row.block_id: {
            "total_detections": int(row.total_detections or 0),
            "healthy_detections": int(row.healthy_detections or 0),
        }
        for row in block_totals_rows
    }

    block_disease_rows = (
        db.query(
            DiseaseDetection.block_id.label("block_id"),
            Disease.id.label("disease_id"),
            Disease.name.label("disease_name"),
            func.count(DiseaseDetection.id).label("frequency"),
        )
        .join(Disease, Disease.id == DiseaseDetection.disease_id)
        .filter(
            DiseaseDetection.block_id.isnot(None),
            func.lower(func.trim(Disease.name)) != HEALTHY_DISEASE_LABEL,
        )
    )
    block_disease_rows = _apply_detection_filters(
        block_disease_rows, start_date, end_date, block_id, disease_id
    ).group_by(
        DiseaseDetection.block_id, Disease.id, Disease.name
    ).order_by(
        DiseaseDetection.block_id.asc(),
        func.count(DiseaseDetection.id).desc(),
        Disease.name.asc(),
    ).all()

    diseases_by_block = {}
    for row in block_disease_rows:
        diseases_by_block.setdefault(row.block_id, []).append(
            {
                "disease_id": row.disease_id,
                "disease_name": row.disease_name,
                "frequency": int(row.frequency),
            }
        )

    distribution_rows = (
        db.query(
            Disease.id.label("disease_id"),
            Disease.name.label("disease_name"),
            func.count(DiseaseDetection.id).label("frequency"),
            func.count(func.distinct(DiseaseDetection.block_id)).label("affected_blocks"),
        )
        .join(Disease, Disease.id == DiseaseDetection.disease_id)
        .filter(func.lower(func.trim(Disease.name)) != HEALTHY_DISEASE_LABEL)
    )
    distribution_rows = _apply_detection_filters(
        distribution_rows, start_date, end_date, block_id, disease_id
    ).group_by(
        Disease.id, Disease.name
    ).order_by(
        func.count(DiseaseDetection.id).desc(), Disease.name.asc()
    ).all()

    distribution = [
        {
            "disease_id": row.disease_id,
            "disease_name": row.disease_name,
            "frequency": int(row.frequency),
            "affected_blocks": int(row.affected_blocks or 0),
        }
        for row in distribution_rows
    ]

    blocks_query = db.query(PlantationBlock)
    if block_id is not None:
        blocks_query = blocks_query.filter(PlantationBlock.id == block_id)

    blocks = []
    for block in blocks_query.order_by(PlantationBlock.id.asc()).all():
        counts = block_totals.get(
            block.id,
            {"total_detections": 0, "healthy_detections": 0},
        )
        disease_items = diseases_by_block.get(block.id, [])
        highest_frequency = (
            max((item["frequency"] for item in disease_items), default=0)
        )
        most_frequent = [
            item["disease_name"]
            for item in disease_items
            if item["frequency"] == highest_frequency and highest_frequency > 0
        ]

        blocks.append(
            {
                "block_id": block.id,
                # PlantationBlock currently has no name/code column.
                "block_name": f"Block {block.id}",
                "total_detections": counts["total_detections"],
                "healthy_detections": counts["healthy_detections"],
                "diseased_detections": (
                    counts["total_detections"] - counts["healthy_detections"]
                ),
                "diseases": disease_items,
                "most_frequently_detected_diseases": most_frequent,
            }
        )

    highest_frequency_blocks = sorted(
        (
            {
                "block_id": item["block_id"],
                "block_name": item["block_name"],
                "total_detections": item["total_detections"],
            }
            for item in blocks
            if item["total_detections"] > 0
        ),
        key=lambda item: (-item["total_detections"], item["block_id"]),
    )

    return {
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "timezone": "UTC",
        },
        "filters": {
            "block_id": block_id,
            "disease_id": disease_id,
        },
        "summary": {
            "total_detections": total_detections,
            "diseased_detections": total_detections - healthy_detections,
            "healthy_detections": healthy_detections,
            "unassigned_detections": unassigned_detections,
        },
        "blocks": blocks,
        "disease_distribution": distribution,
        "highest_frequency_blocks": highest_frequency_blocks,
    }

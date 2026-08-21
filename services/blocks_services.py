from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.block_activity_log import BlockActivityLog
from app.db.models.harvest_record import HarvestRecord
from app.db.models.plantation_block import PlantationBlock
from app.schemas.block import ActivityLogCreate, BlockCreate, BlockUpdate
from app.schemas.harvest import HarvestRecordCreate


def list_blocks_service(
    db: Session,
    search: Optional[str] = None,
    status: Optional[str] = None,
):
    query = db.query(PlantationBlock)

    if search:
        query = query.filter(PlantationBlock.tea_variety.ilike(f"%{search}%"))

    if status and hasattr(PlantationBlock, "status"):
        query = query.filter(PlantationBlock.status == status)

    blocks = query.order_by(PlantationBlock.id).all()
    return [_build_block_response(db, block) for block in blocks]


def create_block_service(db: Session, data: BlockCreate):
    block = PlantationBlock(**_model_fields_for_block(data.model_dump()))
    db.add(block)
    db.commit()
    db.refresh(block)
    return _build_block_response(db, block)


def get_block_service(db: Session, block_id: int):
    block = _get_block_or_404(db, block_id)
    return _build_block_response(db, block)


def update_block_service(db: Session, block_id: int, data: BlockUpdate):
    block = _get_block_or_404(db, block_id)

    for field, value in _model_fields_for_block(data.model_dump(exclude_none=True)).items():
        setattr(block, field, value)

    db.commit()
    db.refresh(block)
    return _build_block_response(db, block)


def delete_block_service(db: Session, block_id: int):
    block = _get_block_or_404(db, block_id)
    db.delete(block)
    db.commit()


def get_harvest_history_service(db: Session, block_id: int, limit: int = 10):
    _get_block_or_404(db, block_id)

    return (
        db.query(HarvestRecord)
        .filter(HarvestRecord.block_id == block_id)
        .order_by(HarvestRecord.date.desc())
        .limit(limit)
        .all()
    )


def add_harvest_record_service(
    db: Session,
    block_id: int,
    data: HarvestRecordCreate,
):
    _get_block_or_404(db, block_id)

    record = HarvestRecord(block_id=block_id, **data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_block_harvest_summary_service(db: Session, block_id: int):
    block = _get_block_or_404(db, block_id)
    return _build_block_response(db, block)


def get_activities_service(db: Session, block_id: int):
    _get_block_or_404(db, block_id)

    return (
        db.query(BlockActivityLog)
        .filter(BlockActivityLog.block_id == block_id)
        .order_by(BlockActivityLog.timestamp.desc())
        .all()
    )


def add_activity_service(
    db: Session,
    block_id: int,
    data: ActivityLogCreate,
):
    _get_block_or_404(db, block_id)

    log = BlockActivityLog(block_id=block_id, **data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _get_block_or_404(db: Session, block_id: int) -> PlantationBlock:
    block = db.query(PlantationBlock).filter(PlantationBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found")
    return block


def _build_block_response(db: Session, block: PlantationBlock):
    today = date.today()
    last_30_days = today - timedelta(days=30)

    total_harvest_kg = (
        db.query(func.coalesce(func.sum(HarvestRecord.quantity_kg), 0.0))
        .filter(HarvestRecord.block_id == block.id)
        .scalar()
    )

    last_harvest_date = (
        db.query(func.max(HarvestRecord.date))
        .filter(HarvestRecord.block_id == block.id)
        .scalar()
    )

    last_month_harvest_kg = (
        db.query(func.coalesce(func.sum(HarvestRecord.quantity_kg), 0.0))
        .filter(
            HarvestRecord.block_id == block.id,
            HarvestRecord.date >= last_30_days,
            HarvestRecord.date <= today,
        )
        .scalar()
    )

    return {
        "id": block.id,
        "area": block.area,
        "tea_variety": block.tea_variety,
        "year_planted": getattr(block, "year_planted", None),
        "supervisor_id": block.supervisor_id,
        "status": getattr(block, "status", None),
        "total_harvest_kg": float(total_harvest_kg or 0),
        "last_harvest_date": last_harvest_date,
        "last_month_harvest_kg": float(last_month_harvest_kg or 0),
    }


def _model_fields_for_block(values: dict):
    return {
        field: value
        for field, value in values.items()
        if hasattr(PlantationBlock, field)
    }

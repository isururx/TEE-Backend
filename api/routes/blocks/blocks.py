from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.block_activity_log import BlockActivityLog
from app.db.models.harvest_record import HarvestRecord
from app.db.models.plantation_block import PlantationBlock
from app.schemas.block import (
    ActivityLogCreate,
    ActivityLogOut,
    BlockCreate,
    BlockOut,
    BlockUpdate,
)
from app.schemas.harvest import HarvestRecordOut

router = APIRouter()


# ── GET /api/blocks ──────────────────────────────────────────────────────────

@router.get("", response_model=List[BlockOut])
def list_blocks(
    search: Optional[str] = Query(None, description="Search by tea variety"),
    status: Optional[str] = Query(None, description="Filter by status (Active/Inactive)"),
    db: Session = Depends(get_db),
):
    query = db.query(PlantationBlock)

    if search:
        query = query.filter(
            PlantationBlock.tea_variety.ilike(f"%{search}%")
        )

    if status:
        query = query.filter(PlantationBlock.status == status)

    return query.order_by(PlantationBlock.id).all()


# ── POST /api/blocks ─────────────────────────────────────────────────────────

@router.post("", response_model=BlockOut, status_code=201)
def create_block(data: BlockCreate, db: Session = Depends(get_db)):
    block = PlantationBlock(**data.model_dump())
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


# ── GET /api/blocks/{block_id} ───────────────────────────────────────────────

@router.get("/{block_id}", response_model=BlockOut)
def get_block(block_id: int, db: Session = Depends(get_db)):
    block = _get_block_or_404(block_id, db)
    return block


# ── PUT /api/blocks/{block_id} ───────────────────────────────────────────────

@router.put("/{block_id}", response_model=BlockOut)
def update_block(
    block_id: int,
    data: BlockUpdate,
    db: Session = Depends(get_db),
):
    block = _get_block_or_404(block_id, db)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(block, field, value)

    db.commit()
    db.refresh(block)
    return block


# ── DELETE /api/blocks/{block_id} ────────────────────────────────────────────

@router.delete("/{block_id}", status_code=204)
def delete_block(block_id: int, db: Session = Depends(get_db)):
    block = _get_block_or_404(block_id, db)
    db.delete(block)
    db.commit()


# ── GET /api/blocks/{block_id}/harvest-history ───────────────────────────────

@router.get("/{block_id}/harvest-history", response_model=List[HarvestRecordOut])
def get_harvest_history(
    block_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    _get_block_or_404(block_id, db)

    records = (
        db.query(HarvestRecord)
        .filter(HarvestRecord.block_id == block_id)
        .order_by(HarvestRecord.date.desc())
        .limit(limit)
        .all()
    )
    return records


# ── GET /api/blocks/{block_id}/activities ────────────────────────────────────

@router.get("/{block_id}/activities", response_model=List[ActivityLogOut])
def get_activities(block_id: int, db: Session = Depends(get_db)):
    _get_block_or_404(block_id, db)

    logs = (
        db.query(BlockActivityLog)
        .filter(BlockActivityLog.block_id == block_id)
        .order_by(BlockActivityLog.timestamp.desc())
        .all()
    )
    return logs


# ── POST /api/blocks/{block_id}/activities ───────────────────────────────────

@router.post("/{block_id}/activities", response_model=ActivityLogOut, status_code=201)
def add_activity(
    block_id: int,
    data: ActivityLogCreate,
    db: Session = Depends(get_db),
):
    _get_block_or_404(block_id, db)

    log = BlockActivityLog(block_id=block_id, **data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_block_or_404(block_id: int, db: Session) -> PlantationBlock:
    block = db.query(PlantationBlock).filter(PlantationBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found")
    return block

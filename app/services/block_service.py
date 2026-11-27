from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, timedelta
from fastapi import HTTPException

from app.db.models.plantation_block import PlantationBlock
from app.db.models.user import User
from app.db.models.harvest_record import HarvestRecord
from app.db.models.block_activity_log import BlockActivityLog
from app.schemas.block import BlockCreate, BlockUpdate, HarvestRecordCreate


def log_block_event(
    db: Session,
    block_id: int,
    title: str,
    operator: Optional[str] = None,
    commit: bool = True,
) -> BlockActivityLog:
    """MT-14: Central helper for writing block timeline events.

    All cross-entity hooks (tasks, harvest, attendance, detection,
    inventory) should call this instead of constructing
    ``BlockActivityLog`` rows inline, so title/operator conventions
    and commit behaviour stay consistent.

    Args:
        db: Active SQLAlchemy session.
        block_id: Target plantation block id (FK, required).
        title: Short human-readable event title, e.g.
            ``"Task #3 marked FINISHED"``.
        operator: Who triggered the event (worker/supervisor name,
            ``"System"``, ...). Nullable.
        commit: When True (default) the row is committed immediately.
            Pass ``commit=False`` when the caller will commit the
            surrounding transaction itself (avoids partial commits).

    Returns:
        The persisted (refreshed when committed) ``BlockActivityLog``.
    """
    if not title or not title.strip():
        raise HTTPException(status_code=400, detail="Activity title is required")

    log = BlockActivityLog(
        block_id=block_id,
        title=title.strip(),
        operator=operator,
    )
    db.add(log)
    if commit:
        db.commit()
        db.refresh(log)
    else:
        db.flush()
    return log


def calculate_block_stats(block: PlantationBlock, db: Session) -> dict:
    total_harvest = db.query(func.coalesce(func.sum(HarvestRecord.quantity_kg), 0.0)).filter(
        HarvestRecord.block_id == block.id
    ).scalar() or 0.0

    last_harvest_date = db.query(func.max(HarvestRecord.date)).filter(
        HarvestRecord.block_id == block.id
    ).scalar()

    thirty_days_ago = date.today() - timedelta(days=30)
    last_month_harvest = db.query(func.coalesce(func.sum(HarvestRecord.quantity_kg), 0.0)).filter(
        HarvestRecord.block_id == block.id,
        HarvestRecord.date >= thirty_days_ago
    ).scalar() or 0.0

    supervisor_name = "Unassigned"
    if block.supervisor_id:
        supervisor = db.query(User).filter(User.id == block.supervisor_id).first()
        if supervisor:
            supervisor_name = supervisor.name

    return {
        "id": block.id,
        "area": block.area,
        "tea_variety": block.tea_variety or "--",
        "plant_date": block.plant_date,
        "supervisor_id": block.supervisor_id,
        "supervisor_name": supervisor_name,
        "total_harvest_kg": round(float(total_harvest), 1),
        "last_harvest_date": last_harvest_date.strftime("%b %d, %Y") if last_harvest_date else "--",
        "last_month_harvest_kg": round(float(last_month_harvest), 1),
        "health_status": "Healthy",
    }


def get_all_blocks(db: Session, search: Optional[str] = None) -> List[dict]:
    query = db.query(PlantationBlock)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (PlantationBlock.tea_variety.ilike(search_pattern)) |
            (PlantationBlock.id.cast(PlantationBlock.id.type).like(search_pattern))
        )
    blocks = query.order_by(PlantationBlock.id.asc()).all()
    return [calculate_block_stats(b, db) for b in blocks]


def get_block_by_id(db: Session, block_id: int) -> dict:
    block = db.query(PlantationBlock).filter(PlantationBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found")
    return calculate_block_stats(block, db)


def create_new_block(db: Session, data: BlockCreate) -> dict:
    if data.supervisor_id:
        supervisor = db.query(User).filter(User.id == data.supervisor_id).first()
        if not supervisor:
            raise HTTPException(status_code=400, detail="Supervisor not found")

    new_block = PlantationBlock(
        area=data.area,
        tea_variety=data.tea_variety,
        plant_date=data.plant_date or date.today(),
        supervisor_id=data.supervisor_id,
    )
    if data.id:
        existing = db.query(PlantationBlock).filter(PlantationBlock.id == data.id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Block with ID {data.id} already exists")
        new_block.id = data.id

    db.add(new_block)
    db.commit()
    db.refresh(new_block)

    # MT-18a: creation log via helper (own commit — block id only exists after the commit above).
    log_block_event(
        db,
        block_id=new_block.id,
        title="Block Registered",
        operator="System Admin",
    )

    return calculate_block_stats(new_block, db)


def update_block_details(db: Session, block_id: int, data: BlockUpdate) -> dict:
    block = db.query(PlantationBlock).filter(PlantationBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found")

    # MT-18b: track which editable fields actually changed for the timeline title.
    changed = []
    if data.area is not None and data.area != block.area:
        changed.append("area")
        block.area = data.area
    if data.tea_variety is not None and data.tea_variety != block.tea_variety:
        changed.append("tea variety")
        block.tea_variety = data.tea_variety
    if data.plant_date is not None and data.plant_date != block.plant_date:
        changed.append("plant date")
        block.plant_date = data.plant_date
    if data.supervisor_id is not None and data.supervisor_id != block.supervisor_id:
        changed.append("supervisor")
        block.supervisor_id = data.supervisor_id

    # Edit log in the same transaction (commit=False; single commit below).
    if changed:
        log_block_event(
            db,
            block_id=block_id,
            title=f"Block Updated ({', '.join(changed)})",
            operator="System Admin",
            commit=False,
        )

    db.commit()
    db.refresh(block)
    return calculate_block_stats(block, db)


def delete_block_by_id(db: Session, block_id: int) -> None:
    block = db.query(PlantationBlock).filter(PlantationBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found")

    db.delete(block)
    db.commit()
    return None


def get_harvest_history(db: Session, block_id: int) -> List[HarvestRecord]:
    return (
        db.query(HarvestRecord)
        .filter(HarvestRecord.block_id == block_id)
        .order_by(HarvestRecord.date.desc())
        .all()
    )


def add_harvest_entry(db: Session, block_id: int, data: HarvestRecordCreate) -> HarvestRecord:
    block = db.query(PlantationBlock).filter(PlantationBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found")

    record = HarvestRecord(
        block_id=block_id,
        date=data.date,
        tea_variety=data.tea_variety or block.tea_variety,
        quantity_kg=data.quantity_kg,
        efficiency_pct=data.efficiency_pct,
        status=data.status or "VERIFIED",
    )
    db.add(record)

    # MT-16: harvest creation -> block timeline via helper, same transaction
    # (commit=False; single commit below keeps record + log atomic).
    log_block_event(
        db,
        block_id=block_id,
        title=f"Harvest Logged ({data.quantity_kg} kg)",
        operator="Field Supervisor",
        commit=False,
    )

    db.commit()
    db.refresh(record)
    return record


def get_block_activities(db: Session, block_id: int) -> List[BlockActivityLog]:
    return (
        db.query(BlockActivityLog)
        .filter(BlockActivityLog.block_id == block_id)
        .order_by(BlockActivityLog.timestamp.desc())
        .all()
    )


def delete_harvest_record(db: Session, block_id: int, record_id: int) -> None:
    block = db.query(PlantationBlock).filter(PlantationBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found")

    record = db.query(HarvestRecord).filter(
        HarvestRecord.id == record_id,
        HarvestRecord.block_id == block_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Harvest record {record_id} not found for block {block_id}")

    db.delete(record)

    # MT-17: harvest deletion -> block timeline via helper, same transaction
    # (commit=False; single commit below keeps delete + log atomic).
    log_block_event(
        db,
        block_id=block_id,
        title=f"Harvest Record Deleted (ID: {record_id})",
        operator="Manager",
        commit=False,
    )
    db.commit()


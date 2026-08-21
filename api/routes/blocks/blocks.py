from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.block import (
    ActivityLogCreate,
    ActivityLogOut,
    BlockCreate,
    BlockOut,
    BlockUpdate,
)
from app.schemas.harvest import HarvestRecordCreate, HarvestRecordOut
from app.services.blocks_services import (
    add_activity_service,
    add_harvest_record_service,
    create_block_service,
    delete_block_service,
    get_activities_service,
    get_block_service,
    get_harvest_history_service,
    list_blocks_service,
    update_block_service,
)

router = APIRouter()


@router.get("", response_model=List[BlockOut])
def list_blocks(
    search: Optional[str] = Query(None, description="Search by tea variety"),
    status: Optional[str] = Query(None, description="Filter by status (Active/Inactive)"),
    db: Session = Depends(get_db),
):
    return list_blocks_service(db=db, search=search, status=status)


@router.post("", response_model=BlockOut, status_code=201)
def create_block(data: BlockCreate, db: Session = Depends(get_db)):
    return create_block_service(db=db, data=data)


@router.get("/{block_id}", response_model=BlockOut)
def get_block(block_id: int, db: Session = Depends(get_db)):
    return get_block_service(db=db, block_id=block_id)


@router.put("/{block_id}", response_model=BlockOut)
def update_block(
    block_id: int,
    data: BlockUpdate,
    db: Session = Depends(get_db),
):
    return update_block_service(db=db, block_id=block_id, data=data)


@router.delete("/{block_id}", status_code=204)
def delete_block(block_id: int, db: Session = Depends(get_db)):
    delete_block_service(db=db, block_id=block_id)


@router.get("/{block_id}/harvest-history", response_model=List[HarvestRecordOut])
def get_harvest_history(
    block_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return get_harvest_history_service(db=db, block_id=block_id, limit=limit)


@router.post("/{block_id}/harvest-history", response_model=HarvestRecordOut, status_code=201)
def add_harvest_record(
    block_id: int,
    data: HarvestRecordCreate,
    db: Session = Depends(get_db),
):
    return add_harvest_record_service(db=db, block_id=block_id, data=data)


@router.get("/{block_id}/activities", response_model=List[ActivityLogOut])
def get_activities(block_id: int, db: Session = Depends(get_db)):
    return get_activities_service(db=db, block_id=block_id)


@router.post("/{block_id}/activities", response_model=ActivityLogOut, status_code=201)
def add_activity(
    block_id: int,
    data: ActivityLogCreate,
    db: Session = Depends(get_db),
):
    return add_activity_service(db=db, block_id=block_id, data=data)

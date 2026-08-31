from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.db.database import get_db
from app.schemas.block import (
    BlockCreate,
    BlockUpdate,
    BlockResponse,
    HarvestRecordCreate,
    HarvestRecordResponse,
    BlockActivityLogResponse,
)
from app.services import block_service

router = APIRouter()


@router.get("", response_model=List[BlockResponse])
def get_blocks(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return block_service.get_all_blocks(db, search)


@router.get("/{block_id}", response_model=BlockResponse)
def get_block(block_id: int, db: Session = Depends(get_db)):
    return block_service.get_block_by_id(db, block_id)


@router.post("", response_model=BlockResponse, status_code=201)
def create_block(data: BlockCreate, db: Session = Depends(get_db)):
    return block_service.create_new_block(db, data)


@router.put("/{block_id}", response_model=BlockResponse)
def update_block(block_id: int, data: BlockUpdate, db: Session = Depends(get_db)):
    return block_service.update_block_details(db, block_id, data)


@router.delete("/{block_id}", status_code=204)
def delete_block(block_id: int, db: Session = Depends(get_db)):
    return block_service.delete_block_by_id(db, block_id)


@router.get("/{block_id}/harvest-history", response_model=List[HarvestRecordResponse])
def get_harvest_history(block_id: int, db: Session = Depends(get_db)):
    return block_service.get_harvest_history(db, block_id)


@router.post("/{block_id}/harvest-history", response_model=HarvestRecordResponse, status_code=201)
def add_harvest_entry(block_id: int, data: HarvestRecordCreate, db: Session = Depends(get_db)):
    return block_service.add_harvest_entry(db, block_id, data)


@router.delete("/{block_id}/harvest-history/{record_id}", status_code=204)
def delete_harvest_entry(block_id: int, record_id: int, db: Session = Depends(get_db)):
    block_service.delete_harvest_record(db, block_id, record_id)


@router.get("/{block_id}/activities", response_model=List[BlockActivityLogResponse])
def get_block_activities(block_id: int, db: Session = Depends(get_db)):
    return block_service.get_block_activities(db, block_id)


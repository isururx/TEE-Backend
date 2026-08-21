from pydantic import BaseModel
from typing import Optional
from datetime import date


class HarvestRecordCreate(BaseModel):
    date: date
    tea_variety: Optional[str] = None
    quantity_kg: Optional[float] = None
    efficiency_pct: Optional[float] = None
    # VERIFIED / FLAGGED
    status: Optional[str] = "VERIFIED"


class HarvestRecordOut(BaseModel):
    id: int
    block_id: int
    date: date
    tea_variety: Optional[str] = None
    quantity_kg: Optional[float] = None
    efficiency_pct: Optional[float] = None
    # VERIFIED / FLAGGED
    status: Optional[str] = None

    model_config = {"from_attributes": True}

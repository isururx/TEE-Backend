from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


# ── Block schemas ────────────────────────────────────────────────────────────

class BlockCreate(BaseModel):
    area: float
    tea_variety: Optional[str] = None
    year_planted: Optional[int] = None
    supervisor_id: Optional[int] = None
    status: Optional[str] = "Active"


class BlockUpdate(BaseModel):
    area: Optional[float] = None
    tea_variety: Optional[str] = None
    year_planted: Optional[int] = None
    supervisor_id: Optional[int] = None
    status: Optional[str] = None


class BlockOut(BaseModel):
    id: int
    area: float
    tea_variety: Optional[str] = None
    year_planted: Optional[int] = None
    supervisor_id: Optional[int] = None
    status: Optional[str] = None
    total_harvest_kg: Optional[float] = None
    last_harvest_date: Optional[date] = None
    last_month_harvest_kg: Optional[float] = None

    model_config = {"from_attributes": True}


# ── Block activity log schemas ───────────────────────────────────────────────

class ActivityLogCreate(BaseModel):
    # Spraying / Pruning / Soil Sampling / etc.
    title: str
    operator: Optional[str] = None


class ActivityLogOut(BaseModel):
    id: int
    block_id: int
    title: str
    operator: Optional[str] = None
    timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}

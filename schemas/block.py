from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class BlockCreate(BaseModel):
    id: Optional[int] = None
    area: float
    tea_variety: Optional[str] = None
    plant_date: Optional[date] = None
    supervisor_id: Optional[int] = None


class BlockUpdate(BaseModel):
    area: Optional[float] = None
    tea_variety: Optional[str] = None
    plant_date: Optional[date] = None
    supervisor_id: Optional[int] = None


class HarvestRecordCreate(BaseModel):
    date: date
    tea_variety: Optional[str] = None
    quantity_kg: float
    efficiency_pct: Optional[float] = None
    status: Optional[str] = "VERIFIED"


class HarvestRecordResponse(BaseModel):
    id: int
    block_id: int
    date: date
    tea_variety: Optional[str] = None
    quantity_kg: Optional[float] = None
    efficiency_pct: Optional[float] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True


class BlockActivityLogResponse(BaseModel):
    id: int
    block_id: int
    title: str
    operator: Optional[str] = None
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


class BlockResponse(BaseModel):
    id: int
    area: float
    tea_variety: Optional[str] = None
    plant_date: Optional[date] = None
    supervisor_id: Optional[int] = None
    supervisor_name: Optional[str] = None
    total_harvest_kg: float = 0.0
    last_harvest_date: Optional[str] = "--"
    last_month_harvest_kg: float = 0.0
    health_status: str = "Healthy"

    class Config:
        from_attributes = True

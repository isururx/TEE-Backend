from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Initialize inventory schema file (Step 6)

class InventoryItemBase(BaseModel):
    name: str
    category: str
    unit: str = "kg"
    min_threshold: float = 10.0
    supplier_id: Optional[int] = None

class InventoryItemCreate(InventoryItemBase):
    pass

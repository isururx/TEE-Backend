from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate

# Initialize supplier service file (Step 14)

def get_all_suppliers(db: Session, skip: int = 0, limit: int = 100) -> List[Supplier]:
    """Retrieve all suppliers with optional pagination."""
    return db.query(Supplier).offset(skip).limit(limit).all()

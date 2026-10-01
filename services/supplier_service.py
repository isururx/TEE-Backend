from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException, status
from app.db.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate

# Initialize supplier service file (Step 14)

def get_all_suppliers(db: Session, skip: int = 0, limit: int = 100) -> List[Supplier]:
    """Retrieve all suppliers with optional pagination."""
    return db.query(Supplier).offset(skip).limit(limit).all()

def get_supplier_by_id(db: Session, supplier_id: int) -> Supplier:
    """Retrieve a supplier by ID, raising 404 if not found."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier with ID {supplier_id} not found"
        )
    return supplier

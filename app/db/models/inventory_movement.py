from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id = Column(
        Integer,
        ForeignKey("inventory_items.id"),
        nullable=False
    )
    movement_type = Column(String, nullable=False)  # "IN" or "OUT"
    quantity = Column(Float, nullable=False)
    purpose = Column(String, nullable=True)
    block_id = Column(
        Integer,
        ForeignKey("plantation_blocks.id"),
        nullable=True
    )
    recorded_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    item = relationship("InventoryItem", back_populates="movements")
    block = relationship("PlantationBlock", foreign_keys=[block_id])
    user = relationship("User", foreign_keys=[recorded_by])

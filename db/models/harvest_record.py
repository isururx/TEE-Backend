from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class HarvestRecord(Base):
    __tablename__ = "harvest_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    block_id = Column(
        Integer,
        ForeignKey("plantation_blocks.id"),
        nullable=False
    )
    date = Column(Date, nullable=False)
    tea_variety = Column(String, nullable=True)
    quantity_kg = Column(Float, nullable=True)
    efficiency_pct = Column(Float, nullable=True)
    status = Column(String, nullable=True)

    # Relationships
    block = relationship("PlantationBlock", back_populates="harvest_records")

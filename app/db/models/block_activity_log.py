from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class BlockActivityLog(Base):
    __tablename__ = "block_activity_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    block_id = Column(
        Integer,
        ForeignKey("plantation_blocks.id"),
        nullable=False
    )
    title = Column(String, nullable=False)
    operator = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    block = relationship("PlantationBlock", back_populates="activity_logs")

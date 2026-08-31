from sqlalchemy import Column, BigInteger, Integer, Date, Time, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    worker_id = Column(
        BigInteger,
        ForeignKey("workers.id"),
        nullable=False
    )
    Date = Column(Date, nullable=False)
    check_in_time = Column(Time, nullable=False)
    assigned_block_id = Column(
        Integer,
        ForeignKey("plantation_blocks.id"),
        nullable=True
    )
    status = Column(Text, nullable=False, default="Active")

    # Relationships
    worker = relationship("Worker", back_populates="attendance_records")
    block = relationship("PlantationBlock", foreign_keys=[assigned_block_id])

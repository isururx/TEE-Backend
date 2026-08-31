from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class PlantationBlock(Base):
    __tablename__ = "plantation_blocks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    area = Column(Float, nullable=False)
    tea_variety = Column(String, nullable=True)
    plant_date = Column(Date, nullable=True)
    supervisor_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    # Relationships
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    harvest_records = relationship("HarvestRecord", back_populates="block", cascade="all, delete-orphan")
    activity_logs = relationship("BlockActivityLog", back_populates="block", cascade="all, delete-orphan")
    workers = relationship("Worker", back_populates="block")
    disease_detections = relationship("DiseaseDetection", foreign_keys="DiseaseDetection.block_id")
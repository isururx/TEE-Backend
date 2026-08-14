from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey
)

from app.db.database import Base


class DiseaseDetection(Base):
    __tablename__ = "disease_detections"

    id = Column(Integer, primary_key=True, index=True)

    disease_id = Column(
        Integer,
        ForeignKey("diseases.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    block_id = Column(
        Integer,
        ForeignKey("plantation_blocks.id"),
        nullable=True
    )

    image_path = Column(String, nullable=False)

    confidence_score = Column(Float, nullable=False)

    timestamp = Column(
        DateTime,
        nullable=False
    )
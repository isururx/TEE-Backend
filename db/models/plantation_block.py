from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from app.db.database import Base


class PlantationBlock(Base):
    __tablename__ = "plantation_blocks"

    id = Column(Integer, primary_key=True, index=True)

    area = Column(Float, nullable=False)

    tea_variety = Column(String)

    plant_date = Column(Date)

    supervisor_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )
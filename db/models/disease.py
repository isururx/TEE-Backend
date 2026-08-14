from sqlalchemy import Column, Integer, String, Text
from app.db.database import Base


class Disease(Base):
    __tablename__ = "diseases"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, unique=True, nullable=False, index=True)

    description = Column(Text)
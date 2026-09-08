from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    contact_name = Column(String, nullable=True)
    phone_num = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    location = Column(String, nullable=True)
    categories = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


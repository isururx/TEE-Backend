from sqlalchemy import Column, BigInteger, Integer, String, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Worker(Base):
    __tablename__ = "workers"

    id = Column(BigInteger, ForeignKey("users.id"), primary_key=True, index=True)
    name = Column(String, nullable=False)
    NIC = Column(BigInteger, nullable=False)
    dob = Column(Date, nullable=False)
    address = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone_num = Column(BigInteger, nullable=False)
    assigned_block = Column(
        Integer,
        ForeignKey("plantation_blocks.id"),
        nullable=True
    )
    password = Column(Text, nullable=False)

    # Relationships
    block = relationship("PlantationBlock", back_populates="workers")
    attendance_records = relationship("Attendance", back_populates="worker", cascade="all, delete-orphan")
    tasks = relationship("Task", secondary="task_workers", back_populates="workers")

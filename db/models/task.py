from sqlalchemy import Column, BigInteger, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    description = Column(Text, nullable=False)
    deadline = Column(DateTime, nullable=True)
    priority = Column(Text, nullable=False, default="MEDIUM")
    status = Column(Text, nullable=False, default="QUEUED")
    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    plantation_block_id = Column(
        Integer,
        ForeignKey("plantation_blocks.id"),
        nullable=False
    )

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    block = relationship("PlantationBlock", foreign_keys=[plantation_block_id])
    workers = relationship("Worker", secondary="task_workers", back_populates="tasks")


class TaskWorker(Base):
    __tablename__ = "task_workers"

    task_id = Column(
        BigInteger,
        ForeignKey("tasks.id"),
        primary_key=True
    )
    worker_id = Column(
        BigInteger,
        ForeignKey("workers.id"),
        primary_key=True
    )

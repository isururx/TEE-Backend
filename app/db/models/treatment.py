from sqlalchemy import Column, Integer, String, Text, ForeignKey
from app.db.database import Base


class Treatment(Base):
    __tablename__ = "treatments"

    id = Column(Integer, primary_key=True, index=True)

    disease_id = Column(
        Integer,
        ForeignKey("diseases.id"),
        nullable=False
    )

    treatment = Column(Text, nullable=False)

    application_method = Column(Text)

    precautions = Column(Text)

    description = Column(Text)
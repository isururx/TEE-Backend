from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from app.db.database import Base

class AuthChallenge(Base):
    __tablename__ = 'auth_challenges'
    __table_args__ = (Index('ix_auth_challenge_purpose_destination', 'purpose', 'destination'),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)
    purpose = Column(String(32), nullable=False, index=True)
    destination = Column(String(320), nullable=False)
    otp_hash = Column(String(64), nullable=True)
    token_hash = Column(String(64), nullable=True, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
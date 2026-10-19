from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, TimestampMixin, utc_now


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    caller_connection_id = Column(String(36), ForeignKey("phone_connections.id", ondelete="SET NULL"), nullable=True)
    
    status = Column(String(50), default="draft", index=True, nullable=False)
    # draft, scheduled, running, paused, completed, cancelled, failed
    
    allowed_start_hour = Column(String(5), default="09:00", nullable=False)
    allowed_end_hour = Column(String(5), default="20:00", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    retry_delay_minutes = Column(Integer, default=60, nullable=False)
    concurrency_limit = Column(Integer, default=2, nullable=False)
    
    total_contacts = Column(Integer, default=0, nullable=False)
    successful_calls = Column(Integer, default=0, nullable=False)
    failed_calls = Column(Integer, default=0, nullable=False)

    # Relationships
    contacts = relationship("CampaignContact", back_populates="campaign", cascade="all, delete-orphan")


class CampaignContact(Base):
    __tablename__ = "campaign_contacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True, nullable=False)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="CASCADE"), index=True, nullable=False)
    status = Column(String(50), default="pending", index=True, nullable=False)
    # pending, calling, completed, failed, opted_out
    attempts_count = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime, nullable=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    campaign = relationship("Campaign", back_populates="contacts")

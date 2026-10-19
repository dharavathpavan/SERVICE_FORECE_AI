from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, TimestampMixin, utc_now


class Contact(Base, TimestampMixin):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    phone_number = Column(String(50), index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), index=True, nullable=True)
    tags = Column(SQLiteJSON, default=list)
    notes = Column(Text, nullable=True)
    custom_fields = Column(SQLiteJSON, default=dict)
    consent_source = Column(String(100), default="direct_inbound", nullable=False)
    consent_timestamp = Column(DateTime, default=utc_now, nullable=False)
    is_suppressed = Column(Boolean, default=False, index=True, nullable=False)


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    phone_number = Column(String(50), index=True, nullable=False)
    consent_type = Column(String(50), default="voice_calls", nullable=False)
    consent_source = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False)
    ip_or_method = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class SuppressionEntry(Base):
    __tablename__ = "suppression_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    phone_number = Column(String(50), index=True, nullable=False)
    reason = Column(String(255), default="user_opt_out", nullable=False)
    suppressed_at = Column(DateTime, default=utc_now, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

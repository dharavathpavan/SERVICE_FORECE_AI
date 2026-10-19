from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Float
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, TimestampMixin, utc_now


class Call(Base, TimestampMixin):
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), index=True, nullable=True)
    contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), index=True, nullable=True)
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="SET NULL"), index=True, nullable=True)
    phone_connection_id = Column(String(36), ForeignKey("phone_connections.id", ondelete="SET NULL"), nullable=True)
    
    direction = Column(String(20), default="inbound", nullable=False)  # inbound, outbound
    phone_number = Column(String(50), index=True, nullable=False)
    caller_id = Column(String(50), nullable=True)
    
    status = Column(String(50), default="queued", index=True, nullable=False)
    # queued, ringing, in_progress, completed, transferred, failed, no_answer, busy
    # Deliberately unset until the call actually concludes: a call that is still
    # ringing, or that was never finalised, must not claim a successful outcome.
    outcome = Column(String(50), index=True, nullable=True)
    # ai_resolved, human_transferred, customer_ended, failed, voicemail
    
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False)
    failure_reason = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    # Carrier/gateway call recording (set by a real telephony adapter). Stays NULL
    # when the carrier does not provide one - the app must not imply otherwise.
    recording_url = Column(String(500), nullable=True)
    # Storage key for the audio the voice provider generated during this call (the
    # AI side only). Written by the audio bridge; served through an authenticated
    # endpoint, never exposed as a public URL.
    agent_audio_key = Column(String(500), nullable=True)
    estimated_cost = Column(Float, default=0.0, nullable=False)

    # Relationships
    events = relationship("CallEvent", back_populates="call", cascade="all, delete-orphan", order_by="CallEvent.created_at")
    transcripts = relationship("Transcript", back_populates="call", cascade="all, delete-orphan", order_by="Transcript.created_at")


class CallEvent(Base):
    __tablename__ = "call_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="CASCADE"), index=True, nullable=False)
    event_type = Column(String(50), nullable=False)  # speech_start, speech_end, barge_in, tool_call, transfer_request, error
    payload = Column(SQLiteJSON, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    call = relationship("Call", back_populates="events")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="CASCADE"), index=True, nullable=False)
    speaker = Column(String(20), nullable=False)  # agent, caller, system
    text = Column(Text, nullable=False)
    start_timestamp_ms = Column(Integer, default=0)
    end_timestamp_ms = Column(Integer, default=0)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    call = relationship("Call", back_populates="transcripts")

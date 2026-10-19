from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, utc_now, TimestampMixin


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    purpose = Column(String(255), default="Customer Support", nullable=False)
    language = Column(String(10), default="en-US", nullable=False)
    voice = Column(String(50), default="Puck", nullable=False)  # Gemini voices: Puck, Charon, Aoede, Fenrir, Kore
    greeting = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=False)
    fallback_behavior = Column(Text, default="Apologize and offer human transfer.", nullable=False)
    direction = Column(String(20), default="both", nullable=False)  # inbound, outbound, both
    max_duration_seconds = Column(Integer, default=600, nullable=False)
    human_transfer_number = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    active_version_number = Column(Integer, default=1, nullable=False)

    # Relationships
    versions = relationship("AgentVersion", back_populates="agent", cascade="all, delete-orphan", order_by="desc(AgentVersion.version_number)")
    tools = relationship("AgentTool", back_populates="agent", cascade="all, delete-orphan")


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number = Column(Integer, nullable=False)
    prompt_snapshot = Column(Text, nullable=False)
    config_snapshot = Column(SQLiteJSON, default=dict)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    agent = relationship("Agent", back_populates="versions")


class AgentTool(Base):
    __tablename__ = "agent_tools"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    tool_name = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    config = Column(SQLiteJSON, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    agent = relationship("Agent", back_populates="tools")

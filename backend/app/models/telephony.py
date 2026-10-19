from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship
from app.models.base import Base, generate_uuid, TimestampMixin


class PhoneConnection(Base, TimestampMixin):
    __tablename__ = "phone_connections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    connection_type = Column(String(50), default="mock", nullable=False)  # mock, gsm_gateway, sip_trunk
    friendly_name = Column(String(255), nullable=False)
    phone_number = Column(String(50), index=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    health_status = Column(String(50), default="healthy", nullable=False)  # healthy, degraded, offline
    last_health_check = Column(DateTime, nullable=True)
    inbound_enabled = Column(Boolean, default=True, nullable=False)
    outbound_enabled = Column(Boolean, default=True, nullable=False)
    assigned_agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    provider_config = Column(SQLiteJSON, default=dict)  # Server-side encrypted or masked configs


class Gateway(Base, TimestampMixin):
    __tablename__ = "gateways"
    # Identifiers only have to be unique inside a tenant: two organizations may
    # both call their gateway "yeastar-tg200" without colliding.
    __table_args__ = (
        UniqueConstraint("organization_id", "identifier", name="uq_gateway_org_identifier"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    identifier = Column(String(100), index=True, nullable=False)
    sip_endpoint = Column(String(255), nullable=False)
    status = Column(String(50), default="online", nullable=False)  # online, offline, unknown
    last_heartbeat = Column(DateTime, nullable=True)
    health_details = Column(SQLiteJSON, default=dict)

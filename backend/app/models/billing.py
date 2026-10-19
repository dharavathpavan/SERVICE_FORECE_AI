from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Float
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from app.models.base import Base, generate_uuid, TimestampMixin, utc_now


class Integration(Base, TimestampMixin):
    __tablename__ = "integrations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(255), nullable=False)
    integration_type = Column(String(50), nullable=False)  # rest_api, webhook, crm, calendar
    is_active = Column(Boolean, default=True, nullable=False)
    config = Column(SQLiteJSON, default=dict)  # Secret fields are masked or encrypted


class WebhookEndpoint(Base, TimestampMixin):
    __tablename__ = "webhook_endpoints"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=False)
    events = Column(SQLiteJSON, default=list)  # list of event names
    is_active = Column(Boolean, default=True, nullable=False)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    webhook_endpoint_id = Column(String(36), ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), index=True, nullable=False)
    event_name = Column(String(100), nullable=False)
    payload = Column(SQLiteJSON, default=dict)
    status = Column(String(50), default="success", nullable=False)  # success, failed, retrying
    status_code = Column(Integer, nullable=True)
    error_message = Column(String(500), nullable=True)
    attempts = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True)
    minutes_used = Column(Float, default=0.0, nullable=False)
    ai_tokens_used = Column(Integer, default=0, nullable=False)
    cost_cents = Column(Integer, default=0, nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    created_at = Column(DateTime, default=utc_now, nullable=False)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    plan_name = Column(String(50), default="starter", nullable=False)  # starter, professional, enterprise
    status = Column(String(50), default="active", nullable=False)  # active, past_due, canceled
    current_period_start = Column(DateTime, default=utc_now, nullable=False)
    current_period_end = Column(DateTime, nullable=True)

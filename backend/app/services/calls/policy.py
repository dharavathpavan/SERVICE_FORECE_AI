"""
Policy engine for inbound and outbound calls.

All limits are enforced **server-side**; the UI is never the source of truth.
Every decision returns machine-readable reason codes plus a user-facing message,
and the caller must honour the decision (answer vs reject vs fallback).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

try:  # zoneinfo needs tzdata on Windows; degrade to UTC if unavailable
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

    class ZoneInfoNotFoundError(Exception):  # type: ignore
        pass

from app.core.config import settings
from app.models.agent import Agent
from app.models.call import Call
from app.models.contact import Contact, SuppressionEntry
from app.models.telephony import PhoneConnection
from app.models.tenant import Organization

logger = logging.getLogger(__name__)

# Reason codes (stable identifiers the frontend can translate).
R_AGENT_DISABLED = "agent_disabled"
R_OUTSIDE_HOURS = "outside_calling_hours"
R_MONTHLY_LIMIT = "monthly_call_limit_reached"
R_LINE_INBOUND_DISABLED = "inbound_disabled_on_line"
R_LINE_OUTBOUND_DISABLED = "outbound_disabled_on_line"
R_LINE_UNVERIFIED = "line_not_verified"
R_SUPPRESSED = "contact_suppressed"
R_NO_CONSENT = "no_consent_on_record"
R_CONCURRENCY = "concurrency_limit_reached"
R_DUPLICATE_CALL = "duplicate_concurrent_call"
R_AGENT_DIRECTION = "agent_direction_mismatch"
R_BUDGET = "daily_budget_exceeded"


@dataclass
class PolicyViolation:
    code: str
    message: str

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


@dataclass
class PolicyDecision:
    allowed: bool
    violations: List[PolicyViolation] = field(default_factory=list)
    #: Suggested handling when not allowed: "human" | "voicemail" | "reject"
    fallback: Optional[str] = None

    def add(self, code: str, message: str) -> None:
        self.violations.append(PolicyViolation(code, message))

    @property
    def codes(self) -> List[str]:
        return [v.code for v in self.violations]

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "violations": [v.to_dict() for v in self.violations],
            "fallback": self.fallback,
        }


def resolve_timezone(name: Optional[str]):
    """Resolve an IANA timezone, falling back to UTC when tzdata is unavailable."""
    if not name or ZoneInfo is None:
        return timezone.utc
    if name.upper() in ("UTC", "GMT", "Z"):
        return timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        logger.warning("Unknown timezone %r; falling back to UTC", name)
        return timezone.utc


def parse_hhmm(value: str) -> time:
    """Parse 'HH:MM' into a time, defaulting to 09:00 on bad input."""
    try:
        hh, mm = value.split(":")
        return time(int(hh) % 24, int(mm) % 60)
    except Exception:
        return time(9, 0)


def within_calling_hours(start: str, end: str, now: datetime, tz_name: Optional[str]) -> bool:
    """Return True when ``now`` falls inside [start, end) in the given timezone."""
    tz = resolve_timezone(tz_name)
    local_now = now.astimezone(tz).time() if now.tzinfo else now.time()
    start_t, end_t = parse_hhmm(start), parse_hhmm(end)
    if start_t <= end_t:
        return start_t <= local_now < end_t
    # Window crosses midnight (e.g. 22:00 -> 06:00)
    return local_now >= start_t or local_now < end_t


class PolicyEngine:
    """Evaluates business rules for a call before any telephony action."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    # Shared checks
    # ------------------------------------------------------------------ #
    def _calls_this_month(self, organization_id: str, now: datetime) -> int:
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return (
            self.db.query(func.count(Call.id))
            .filter(Call.organization_id == organization_id, Call.created_at >= month_start)
            .scalar()
            or 0
        )

    def _active_call_count(self, organization_id: str) -> int:
        return (
            self.db.query(func.count(Call.id))
            .filter(
                Call.organization_id == organization_id,
                Call.status.in_(["queued", "ringing", "in_progress"]),
            )
            .scalar()
            or 0
        )

    def _is_suppressed(self, organization_id: str, phone_number: str) -> bool:
        entry = (
            self.db.query(SuppressionEntry)
            .filter(
                SuppressionEntry.organization_id == organization_id,
                SuppressionEntry.phone_number == phone_number,
            )
            .first()
        )
        if entry:
            return True
        contact = (
            self.db.query(Contact)
            .filter(Contact.organization_id == organization_id, Contact.phone_number == phone_number)
            .first()
        )
        return bool(contact and contact.is_suppressed)

    # ------------------------------------------------------------------ #
    # Inbound
    # ------------------------------------------------------------------ #
    def evaluate_inbound(
        self,
        organization: Organization,
        connection: Optional[PhoneConnection],
        agent: Optional[Agent],
        now: Optional[datetime] = None,
    ) -> PolicyDecision:
        now = now or datetime.now(timezone.utc)
        decision = PolicyDecision(allowed=True)

        if connection is not None:
            if not connection.inbound_enabled:
                decision.add(R_LINE_INBOUND_DISABLED, "Inbound calls are disabled on this line.")

        if agent is None:
            decision.add(R_AGENT_DISABLED, "No AI agent is assigned to this line.")
            decision.fallback = "human"
            decision.allowed = False
            return decision

        if not agent.is_active:
            decision.add(R_AGENT_DISABLED, "The assigned agent is disabled.")
            decision.fallback = "human"

        if agent.direction not in ("inbound", "both"):
            decision.add(R_AGENT_DIRECTION, "The agent is not configured for inbound calls.")
            decision.fallback = "human"

        if not within_calling_hours(
            settings.DEFAULT_CALLING_HOURS_START,
            settings.DEFAULT_CALLING_HOURS_END,
            now,
            "UTC",
        ):
            # Inbound calls are still answered outside hours, but with a fallback note.
            decision.add(R_OUTSIDE_HOURS, "Outside configured service hours; use after-hours handling.")

        used = self._calls_this_month(organization.id, now)
        if organization.monthly_call_limit and used >= organization.monthly_call_limit:
            decision.add(R_MONTHLY_LIMIT, "Monthly call limit reached for this workspace.")
            decision.fallback = "voicemail"

        decision.allowed = not decision.violations or all(
            v.code == R_OUTSIDE_HOURS for v in decision.violations
        )
        if not decision.allowed and not decision.fallback:
            decision.fallback = "human"
        return decision

    # ------------------------------------------------------------------ #
    # Outbound
    # ------------------------------------------------------------------ #
    def evaluate_outbound(
        self,
        organization: Organization,
        connection: Optional[PhoneConnection],
        agent: Optional[Agent],
        to_number: str,
        *,
        now: Optional[datetime] = None,
        tz_name: Optional[str] = None,
        start_hour: Optional[str] = None,
        end_hour: Optional[str] = None,
        concurrency_limit: Optional[int] = None,
        require_consent: bool = True,
    ) -> PolicyDecision:
        now = now or datetime.now(timezone.utc)
        decision = PolicyDecision(allowed=True)

        if connection is not None:
            if not connection.outbound_enabled:
                decision.add(R_LINE_OUTBOUND_DISABLED, "Outbound calls are disabled on this line.")
            if not connection.is_verified:
                decision.add(R_LINE_UNVERIFIED, "The calling line has not been verified.")

        if agent is None:
            decision.add(R_AGENT_DISABLED, "No AI agent selected for this call.")
        else:
            if not agent.is_active:
                decision.add(R_AGENT_DISABLED, "The selected agent is disabled.")
            if agent.direction not in ("outbound", "both"):
                decision.add(R_AGENT_DIRECTION, "The agent is not configured for outbound calls.")

        start = start_hour or settings.DEFAULT_CALLING_HOURS_START
        end = end_hour or settings.DEFAULT_CALLING_HOURS_END
        if not within_calling_hours(start, end, now, tz_name):
            decision.add(
                R_OUTSIDE_HOURS,
                f"Outside the permitted calling window ({start}-{end}).",
            )

        if self._is_suppressed(organization.id, to_number):
            decision.add(R_SUPPRESSED, "The contact is on the do-not-call suppression list.")

        if require_consent:
            contact = (
                self.db.query(Contact)
                .filter(
                    Contact.organization_id == organization.id,
                    Contact.phone_number == to_number,
                )
                .first()
            )
            if contact is not None and not contact.consent_source:
                decision.add(R_NO_CONSENT, "No recorded consent for this contact.")

        used = self._calls_this_month(organization.id, now)
        if organization.monthly_call_limit and used >= organization.monthly_call_limit:
            decision.add(R_MONTHLY_LIMIT, "Monthly call limit reached for this workspace.")

        limit = concurrency_limit or settings.MAX_CAMPAIGN_CONCURRENCY
        if self._active_call_count(organization.id) >= limit:
            decision.add(R_CONCURRENCY, f"Concurrency limit of {limit} active calls reached.")

        # Block a second concurrent call to the same number.
        duplicate = (
            self.db.query(Call)
            .filter(
                Call.organization_id == organization.id,
                Call.phone_number == to_number,
                Call.status.in_(["queued", "ringing", "in_progress"]),
            )
            .first()
        )
        if duplicate:
            decision.add(R_DUPLICATE_CALL, "A call to this number is already in progress.")

        decision.allowed = not decision.violations
        return decision

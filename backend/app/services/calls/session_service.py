"""
Call session orchestration.

Implements the inbound (§4) and outbound (§5) workflows from the product spec as
explicit, auditable state transitions. The telephony adapter is the only thing
that talks to the carrier; every branch records an honest outcome.

Guarantees:
  * No silent call drops — unserviceable calls are rejected or sent to a fallback.
  * No fake success — adapter errors become ``failed`` calls with a reason code.
  * Every transition emits a ``CallEvent`` and a live hub event.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent import Agent
from app.models.billing import UsageRecord
from app.models.call import Call, CallEvent, Transcript
from app.models.telephony import PhoneConnection
from app.models.tenant import Organization
from app.services.calls.events import EventHub, event_hub
from app.services.calls.policy import PolicyDecision, PolicyEngine
from app.services.telephony.adapter import TelephonyAdapter
from app.services.telephony.factory import get_adapter
from app.services.telephony.types import (
    CallState,
    InboundEvent,
    TelephonyError,
)

logger = logging.getLogger(__name__)

COST_PER_MINUTE = 0.035


@dataclass
class CallOutcome:
    """Result of a session-service action."""

    action: str  # answered | rejected | fallback | initiated | blocked | failed
    message: str
    call: Optional[Call] = None
    decision: Optional[PolicyDecision] = None
    audio_bridge_uri: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "message": self.message,
            "call_id": self.call.id if self.call else None,
            "status": self.call.status if self.call else None,
            "outcome": self.call.outcome if self.call else None,
            "audio_bridge_uri": self.audio_bridge_uri,
            "error": self.error,
            "policy": self.decision.to_dict() if self.decision else None,
        }


class CallSessionService:
    def __init__(
        self,
        db: Session,
        adapter: Optional[TelephonyAdapter] = None,
        hub: Optional[EventHub] = None,
    ) -> None:
        self.db = db
        self.adapter = adapter or get_adapter()
        self.hub = hub or event_hub
        self.policy = PolicyEngine(db)

    # ------------------------------------------------------------------ #
    # Resolution helpers
    # ------------------------------------------------------------------ #
    def resolve_connection(self, organization_id: str, did: Optional[str]) -> Optional[PhoneConnection]:
        if not did:
            return None
        return (
            self.db.query(PhoneConnection)
            .filter(
                PhoneConnection.organization_id == organization_id,
                PhoneConnection.phone_number == did,
            )
            .first()
        )

    def resolve_agent(self, organization_id: str, connection: Optional[PhoneConnection]) -> Optional[Agent]:
        if connection and connection.assigned_agent_id:
            agent = (
                self.db.query(Agent)
                .filter(Agent.id == connection.assigned_agent_id, Agent.organization_id == organization_id)
                .first()
            )
            if agent:
                return agent
        return (
            self.db.query(Agent)
            .filter(Agent.organization_id == organization_id, Agent.is_active.is_(True))
            .order_by(Agent.created_at.asc())
            .first()
        )

    # ------------------------------------------------------------------ #
    # Event emission
    # ------------------------------------------------------------------ #
    def _emit(self, call: Call, event_type: str, payload: Dict[str, Any]) -> None:
        self.db.add(CallEvent(call_id=call.id, event_type=event_type, payload=payload))
        event = {"event_type": event_type, "payload": payload}
        self.hub.publish(call.id, event)

    # ------------------------------------------------------------------ #
    # Inbound workflow (§4)
    # ------------------------------------------------------------------ #
    def handle_inbound(
        self,
        organization: Organization,
        inbound: InboundEvent,
        *,
        now: Optional[datetime] = None,
    ) -> CallOutcome:
        now = now or datetime.now(timezone.utc)
        connection = self.resolve_connection(organization.id, inbound.to_number)
        agent = self.resolve_agent(organization.id, connection)
        decision = self.policy.evaluate_inbound(organization, connection, agent, now=now)

        call = Call(
            organization_id=organization.id,
            agent_id=agent.id if agent else None,
            phone_connection_id=connection.id if connection else None,
            direction="inbound",
            phone_number=inbound.to_number or (connection.phone_number if connection else "unknown"),
            caller_id=inbound.from_number,
            status="ringing",
            start_time=now,
        )
        self.db.add(call)
        self.db.flush()

        self._emit(
            call,
            "call_received",
            {
                "from": inbound.from_number,
                "to": inbound.to_number,
                "line_id": inbound.line_id,
                "raw_event": inbound.event_type,
            },
        )
        self._emit(call, "policy_decision", decision.to_dict())
        self.db.commit()
        self.db.refresh(call)

        if not decision.allowed:
            return self._apply_fallback(call, agent, decision, now, adapter_call_id=inbound.call_id)

        # Answer and bridge audio.
        try:
            self.adapter.answer_call(inbound.call_id)
            bridge_uri = self.adapter.bridge_audio(inbound.call_id)
        except TelephonyError as exc:
            return self._fail(call, exc, action="failed", adapter_call_id=inbound.call_id)

        call.status = "in_progress"
        call.caller_id = call.caller_id or inbound.from_number
        self._emit(call, "call_answered", {"answered_at": now.isoformat()})
        self._emit(call, "audio_bridged", {"uri": bridge_uri})
        self.db.commit()
        self.db.refresh(call)

        return CallOutcome(
            action="answered",
            message="Call answered and bridged to the AI voice session.",
            call=call,
            decision=decision,
            audio_bridge_uri=bridge_uri,
        )

    def _apply_fallback(
        self,
        call: Call,
        agent: Optional[Agent],
        decision: PolicyDecision,
        now: datetime,
        *,
        adapter_call_id: Optional[str] = None,
    ) -> CallOutcome:
        """Honour the configured fallback: human -> voicemail -> polite termination."""
        fallback = decision.fallback or "reject"
        target = agent.human_transfer_number if agent else None
        adapter_call_id = adapter_call_id or call.id

        if fallback == "human" and target:
            try:
                self.adapter.answer_call(adapter_call_id)
                self.adapter.transfer_call(adapter_call_id, target)
                call.status = "transferred"
                call.outcome = "human_transferred"
                call.end_time = now
                self._emit(call, "fallback_human_transfer", {"target": target, "reasons": decision.codes})
                self.db.commit()
                self.db.refresh(call)
                return CallOutcome(
                    action="fallback",
                    message=f"Agent unavailable; transferred to {target}.",
                    call=call,
                    decision=decision,
                )
            except TelephonyError as exc:
                logger.warning("Fallback transfer failed for %s: %s", call.id, exc.message)

        # Voicemail or explicit rejection: never leave the call hanging.
        try:
            self.adapter.reject_call(adapter_call_id, reason=",".join(decision.codes) or "unavailable")
        except TelephonyError as exc:
            logger.warning("Reject failed for %s: %s", call.id, exc.message)

        call.status = "failed"
        call.outcome = "voicemail" if fallback == "voicemail" else "failed"
        call.failure_reason = ",".join(decision.codes) or "unavailable"
        call.end_time = now
        call.duration_seconds = 0
        self._emit(call, "call_rejected", {"reasons": decision.codes, "fallback": fallback})
        self.db.commit()
        self.db.refresh(call)

        return CallOutcome(
            action="fallback" if fallback == "voicemail" else "rejected",
            message=decision.violations[0].message if decision.violations else "Call not serviceable.",
            call=call,
            decision=decision,
        )

    # ------------------------------------------------------------------ #
    # Outbound workflow (§5)
    # ------------------------------------------------------------------ #
    def place_outbound(
        self,
        organization: Organization,
        connection: Optional[PhoneConnection],
        agent: Optional[Agent],
        to_number: str,
        *,
        initiated_by_user_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        contact_id: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        now: Optional[datetime] = None,
    ) -> CallOutcome:
        now = now or datetime.now(timezone.utc)
        decision = self.policy.evaluate_outbound(organization, connection, agent, to_number, now=now)

        from_number = connection.phone_number if connection else "unknown"
        call = Call(
            organization_id=organization.id,
            agent_id=agent.id if agent else None,
            phone_connection_id=connection.id if connection else None,
            campaign_id=campaign_id,
            contact_id=contact_id,
            direction="outbound",
            phone_number=to_number,
            caller_id=from_number,
            status="queued",
            start_time=now,
        )
        self.db.add(call)
        self.db.flush()
        self._emit(call, "outbound_requested", {"to": to_number, "from": from_number, "reason": reason})
        self._emit(call, "policy_decision", decision.to_dict())
        self.db.commit()
        self.db.refresh(call)

        if not decision.allowed:
            call.status = "failed"
            call.outcome = "failed"
            call.failure_reason = ",".join(decision.codes)
            call.end_time = now
            self._emit(call, "outbound_blocked", {"reasons": decision.codes})
            self.db.commit()
            self.db.refresh(call)
            return CallOutcome(
                action="blocked",
                message=decision.violations[0].message if decision.violations else "Call blocked by policy.",
                call=call,
                decision=decision,
            )

        try:
            snapshot = self.adapter.initiate_call(
                to_number=to_number,
                from_number=from_number,
                call_id=call.id,
                line_id=connection.phone_number if connection else None,
                metadata=metadata or {},
            )
        except TelephonyError as exc:
            return self._fail(call, exc, action="failed")

        call.status = snapshot.state.value if snapshot.state else "ringing"
        call.failure_reason = snapshot.failure_reason
        self._emit(call, "outbound_initiated", {"channel": snapshot.channel, "state": call.status})
        self.db.commit()
        self.db.refresh(call)

        return CallOutcome(
            action="initiated",
            message="Outbound call initiated.",
            call=call,
            decision=decision,
        )

    # ------------------------------------------------------------------ #
    # Finalisation
    # ------------------------------------------------------------------ #
    def finalize(
        self,
        call: Call,
        *,
        outcome: Optional[str] = None,
        summary: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> Call:
        """Close a call, write usage, and emit the terminal event."""
        now = datetime.now(timezone.utc)
        call.end_time = call.end_time or now
        if duration_seconds is not None:
            call.duration_seconds = duration_seconds
        elif call.start_time:
            start = call.start_time if call.start_time.tzinfo else call.start_time.replace(tzinfo=timezone.utc)
            call.duration_seconds = max(0, int((now - start).total_seconds()))
        call.outcome = outcome or call.outcome
        call.summary = summary or call.summary
        if call.status in ("queued", "ringing", "in_progress"):
            call.status = "completed"
        call.estimated_cost = round((call.duration_seconds / 60.0) * COST_PER_MINUTE, 4)

        self.db.add(
            UsageRecord(
                organization_id=call.organization_id,
                call_id=call.id,
                minutes_used=round(call.duration_seconds / 60.0, 2),
                ai_tokens_used=0,
                cost_cents=int(call.estimated_cost * 100),
                date=now.strftime("%Y-%m-%d"),
            )
        )
        self._emit(call, "call_completed", {"outcome": call.outcome, "seconds": call.duration_seconds})
        self.db.commit()
        self.db.refresh(call)
        return call

    def add_transcript_turn(self, call: Call, speaker: str, text: str, start_ms: int, end_ms: int) -> Transcript:
        turn = Transcript(
            call_id=call.id,
            speaker=speaker,
            text=text,
            start_timestamp_ms=start_ms,
            end_timestamp_ms=end_ms,
        )
        self.db.add(turn)
        self.db.commit()
        self.hub.publish(call.id, {"event_type": "transcript", "payload": {"speaker": speaker, "text": text}})
        return turn

    def store_agent_audio(
        self,
        call: Call,
        pcm: bytes,
        sample_rate: int,
        *,
        engine: Optional[str] = None,
        content_type: str = "audio/wav",
    ) -> Optional[str]:
        """
        Persist the audio the AI actually produced on this call.

        This is the *agent side only* - the carrier may not record anything, and this
        must never be presented as a full call recording. Storage failures are logged
        and swallowed: a call is not allowed to fail because an artifact could not be
        written.
        """
        if not pcm or sample_rate <= 0:
            return None

        from app.services.storage import StorageError, build_key, get_storage
        from app.services.voice.synthesis import pcm16_to_wav

        key = build_key(call.organization_id, "agent-audio", f"{call.id}.wav")
        try:
            get_storage().put(key, pcm16_to_wav(pcm, sample_rate), content_type=content_type)
        except StorageError:
            logger.exception("Could not store agent audio for call %s", call.id)
            return None

        call.agent_audio_key = key
        self._emit(
            call,
            "agent_audio_stored",
            {
                "seconds": round(len(pcm) / (2 * sample_rate), 2),
                "sample_rate": sample_rate,
                "engine": engine,
                "scope": "agent",
            },
        )
        self.db.commit()
        self.db.refresh(call)
        return key

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _fail(self, call: Call, exc: TelephonyError, *, action: str, adapter_call_id: Optional[str] = None) -> CallOutcome:
        now = datetime.now(timezone.utc)
        call.status = "failed"
        call.outcome = "failed"
        call.failure_reason = exc.code
        call.end_time = now
        self._emit(call, "call_failed", {"error": exc.to_dict()})
        self.db.commit()
        self.db.refresh(call)
        return CallOutcome(
            action=action,
            message=exc.user_message,
            call=call,
            error=exc.to_dict(),
        )

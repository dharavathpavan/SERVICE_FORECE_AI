"""
Mock telephony adapter.

Deterministic and seedable so the same scenario produces the same transcript and
events in tests. It is a *simulator*, not a fake success path: failure modes are
opt-in via ``metadata["simulate"]`` and always raise the correct typed error.
"""
from __future__ import annotations

import random
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.services.telephony.adapter import TelephonyAdapter
from app.services.telephony.types import (
    BusyError,
    CallNotFoundError,
    CallSnapshot,
    CallState,
    Capability,
    CapabilityReport,
    CarrierError,
    ConnectivityResult,
    DeviceInfo,
    Direction,
    HangupCause,
    InboundEvent,
    LineState,
    LineStatus,
    NoAnswerError,
    UnreachableError,
    _utcnow,
)

# Failure modes a caller may request. Kept explicit so tests are readable.
SIMULATIONS = {
    "busy": BusyError,
    "no_answer": NoAnswerError,
    "unreachable": UnreachableError,
    "carrier_error": CarrierError,
}


class MockTelephonyAdapter(TelephonyAdapter):
    """In-memory telephony simulator for development and automated tests."""

    provider_name = "mock"

    def __init__(
        self,
        default_number: str = "+1-800-555-0100",
        carrier: str = "ServiceForce Mock Carrier",
        seed: int = 1337,
    ) -> None:
        self.default_number = default_number
        self.carrier = carrier
        self._rng = random.Random(seed)
        self._calls: Dict[str, CallSnapshot] = {}
        self._booted_at = _utcnow()

    # ------------------------------------------------------------------ #
    # Capabilities
    # ------------------------------------------------------------------ #
    def capabilities(self) -> CapabilityReport:
        return CapabilityReport(
            provider=self.provider_name,
            discovery=Capability.SUPPORTED,
            line_status=Capability.SUPPORTED,
            connectivity_probe=Capability.SUPPORTED,
            inbound_calls=Capability.SUPPORTED,
            outbound_calls=Capability.SUPPORTED,
            bidirectional_audio=Capability.SUPPORTED,
            barge_in=Capability.SUPPORTED,
            transfer=Capability.SUPPORTED,
            reject_call=Capability.SUPPORTED,
            recording=Capability.UNSUPPORTED,
            notes=[
                "Simulation only. No real PSTN/GSM traffic is generated.",
                "Audio bridge points at the local voice WebSocket endpoint.",
            ],
        )

    # ------------------------------------------------------------------ #
    # Discovery / status / connectivity
    # ------------------------------------------------------------------ #
    def discover_devices(self) -> List[DeviceInfo]:
        return [
            DeviceInfo(
                device_id="mock-gw-1",
                vendor="ServiceForce",
                model="Simulated 1-port VoLTE Gateway",
                firmware="sim-1.0.0",
                address="sim://localhost",
                reachable=True,
                lines=self.get_line_status(),
                detail="Synthetic device used when TELEPHONY_PROVIDER=mock.",
            )
        ]

    def get_line_status(self, line_id: Optional[str] = None) -> List[LineStatus]:
        line = LineStatus(
            line_id=line_id or "sim-line-1",
            state=LineState.REGISTERED,
            phone_number=self.default_number,
            carrier=self.carrier,
            signal_percent=self._rng.randint(70, 99),
            registration_ok=True,
            active_channels=self._count_active(),
            max_channels=1,
            sim_present=True,
            detail="Simulated SIM registered on the mock network.",
        )
        return [line]

    def verify_connectivity(self, device_id: Optional[str] = None) -> ConnectivityResult:
        start = time.perf_counter()
        # Deterministic nominal latency with small jitter.
        latency = round(8.0 + self._rng.random() * 6.0, 2)
        return ConnectivityResult(
            ok=True,
            latency_ms=latency,
            message="Mock gateway reachable.",
            detail={
                "device_id": device_id or "mock-gw-1",
                "uptime_seconds": (_utcnow() - self._booted_at).total_seconds(),
                "probe_ms": round((time.perf_counter() - start) * 1000, 3),
            },
        )

    # ------------------------------------------------------------------ #
    # Inbound
    # ------------------------------------------------------------------ #
    def parse_inbound_event(self, payload: Dict[str, Any]) -> InboundEvent:
        call_id = payload.get("call_id") or payload.get("CallId")
        if not call_id:
            from app.services.telephony.types import TelephonyError

            raise TelephonyError("Inbound payload missing call_id", details={"payload": payload})

        event = InboundEvent(
            event_type=payload.get("event_type", "call_received"),
            call_id=str(call_id),
            from_number=payload.get("from_number") or payload.get("CallerNumber"),
            to_number=payload.get("to_number") or payload.get("DialedNumber"),
            line_id=payload.get("line_id", "sim-line-1"),
            channel=payload.get("channel"),
            raw=payload,
        )
        # A real adapter would already know the channel exists; mirror that so
        # answer/reject/bridge operate on a genuine ringing call.
        if event.event_type == "call_received" and event.call_id not in self._calls:
            self.simulate_inbound(
                event.call_id,
                from_number=event.from_number or "+1-555-0000",
                to_number=event.to_number,
            )
        return event

    def simulate_inbound(
        self,
        call_id: str,
        from_number: str = "+1-555-0199",
        to_number: Optional[str] = None,
    ) -> CallSnapshot:
        """Test helper: place a call into the ringing state."""
        snap = CallSnapshot(
            call_id=call_id,
            state=CallState.RINGING,
            direction=Direction.INBOUND,
            from_number=from_number,
            to_number=to_number or self.default_number,
            line_id="sim-line-1",
            channel=f"PJSIP/mock-{call_id[:8]}",
            started_at=_utcnow(),
        )
        self._calls[call_id] = snap
        return snap

    def answer_call(self, call_id: str) -> CallSnapshot:
        snap = self._require(call_id)
        if snap.state not in (CallState.RINGING, CallState.QUEUED):
            from app.services.telephony.types import TelephonyError

            raise TelephonyError(
                "Call is not ringing and cannot be answered.",
                details={"call_id": call_id, "state": snap.state.value},
            )
        snap.state = CallState.IN_PROGRESS
        snap.answered_at = _utcnow()
        return snap

    def reject_call(self, call_id: str, reason: str = "call_rejected") -> CallSnapshot:
        snap = self._require(call_id)
        snap.state = CallState.REJECTED
        snap.ended_at = _utcnow()
        snap.hangup_cause = HangupCause.CALL_REJECTED
        snap.failure_reason = reason
        return snap

    # ------------------------------------------------------------------ #
    # Outbound
    # ------------------------------------------------------------------ #
    def initiate_call(
        self,
        to_number: str,
        from_number: str,
        call_id: str,
        line_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CallSnapshot:
        metadata = metadata or {}
        simulate = metadata.get("simulate")
        if simulate:
            exc_cls = SIMULATIONS.get(simulate, CarrierError)
            snap = CallSnapshot(
                call_id=call_id,
                state=CallState.FAILED,
                direction=Direction.OUTBOUND,
                from_number=from_number,
                to_number=to_number,
                line_id=line_id or "sim-line-1",
                started_at=_utcnow(),
                ended_at=_utcnow(),
                failure_reason=simulate,
            )
            self._calls[call_id] = snap
            raise exc_cls(f"Simulated failure: {simulate}", details={"call_id": call_id})

        snap = CallSnapshot(
            call_id=call_id,
            state=CallState.RINGING,
            direction=Direction.OUTBOUND,
            from_number=from_number,
            to_number=to_number,
            line_id=line_id or "sim-line-1",
            channel=f"PJSIP/mock-out-{call_id[:8]}",
            started_at=_utcnow(),
            metadata=metadata,
        )
        self._calls[call_id] = snap
        return snap

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def get_call_state(self, call_id: str) -> CallSnapshot:
        return self._require(call_id)

    def hangup_call(self, call_id: str, cause: str = "normal_clearing") -> CallSnapshot:
        snap = self._require(call_id)
        snap.state = CallState.COMPLETED
        snap.ended_at = _utcnow()
        try:
            snap.hangup_cause = HangupCause(cause)
        except ValueError:
            snap.hangup_cause = HangupCause.NORMAL_CLEARING
        return snap

    def transfer_call(self, call_id: str, target: str) -> CallSnapshot:
        snap = self._require(call_id)
        snap.state = CallState.TRANSFERRED
        snap.transfer_target = target
        snap.ended_at = _utcnow()
        return snap

    # ------------------------------------------------------------------ #
    # Audio
    # ------------------------------------------------------------------ #
    def bridge_audio(self, call_id: str) -> str:
        snap = self._require(call_id)
        uri = f"ws://localhost:8000/api/v1/voice/stream?call_id={call_id}"
        snap.audio_bridge_uri = uri
        return uri

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _require(self, call_id: str) -> CallSnapshot:
        snap = self._calls.get(call_id)
        if not snap:
            raise CallNotFoundError(f"No such call: {call_id}", details={"call_id": call_id})
        return snap

    def _count_active(self) -> int:
        return sum(
            1
            for c in self._calls.values()
            if c.state in (CallState.RINGING, CallState.IN_PROGRESS)
        )

    # Test convenience
    def reset(self) -> None:
        self._calls.clear()
        self._rng = random.Random(1337)


# Module-level default instance, used by the provider factory.
mock_telephony = MockTelephonyAdapter()

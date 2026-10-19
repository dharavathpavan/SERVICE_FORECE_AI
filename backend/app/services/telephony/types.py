"""
Telephony domain types shared by every adapter.

Design rule: adapters return *typed results*, never bare booleans. A missing or
unimplemented capability is reported as UNSUPPORTED / UNKNOWN, never as success.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #
class Capability(str, Enum):
    """Honest three-state capability flag. Default is UNKNOWN, never SUPPORTED."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class CallState(str, Enum):
    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TRANSFERRED = "transferred"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    REJECTED = "rejected"


class LineState(str, Enum):
    """State of a SIM / voice line as seen by the gateway."""

    REGISTERED = "registered"
    UNREGISTERED = "unregistered"
    NO_SIM = "no_sim"
    SEARCHING = "searching"
    PIN_LOCKED = "pin_locked"
    UNKNOWN = "unknown"


class Direction(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class HangupCause(str, Enum):
    NORMAL_CLEARING = "normal_clearing"
    USER_BUSY = "user_busy"
    NO_ANSWER = "no_answer"
    CALL_REJECTED = "call_rejected"
    NETWORK_FAILURE = "network_failure"
    NORMAL_TEMPORARY_FAILURE = "normal_temporary_failure"
    GATEWAY_OFFLINE = "gateway_offline"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #
class TelephonyError(Exception):
    """Base class for all telephony failures. Always carries a user-safe message."""

    code: str = "telephony_error"
    user_message: str = "The telephony operation could not be completed."
    retryable: bool = False

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        details: Optional[Dict[str, Any]] = None,
        retryable: Optional[bool] = None,
    ) -> None:
        super().__init__(message or self.user_message)
        self.message = message or self.user_message
        self.details = details or {}
        if retryable is not None:
            self.retryable = retryable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.code,
            "message": self.user_message,
            "details": self.details,
            "retryable": self.retryable,
        }


class GatewayOfflineError(TelephonyError):
    code = "gateway_offline"
    user_message = "The voice gateway is offline or not registered. Check the SIM and network."
    retryable = True


class UnreachableError(TelephonyError):
    code = "destination_unreachable"
    user_message = "The destination number is unreachable right now."
    retryable = True


class BusyError(TelephonyError):
    code = "line_busy"
    user_message = "The destination line is busy."
    retryable = True


class NoAnswerError(TelephonyError):
    code = "no_answer"
    user_message = "The call was not answered."
    retryable = True


class CarrierError(TelephonyError):
    code = "carrier_error"
    user_message = "The mobile carrier rejected the call."
    retryable = False


class NotSupportedError(TelephonyError):
    code = "not_supported"
    user_message = "This capability is not supported by the configured telephony adapter."
    retryable = False


class CallNotFoundError(TelephonyError):
    code = "call_not_found"
    user_message = "The requested call session does not exist."
    retryable = False


class AudioBridgeError(TelephonyError):
    code = "audio_bridge_failed"
    user_message = "The two-way audio bridge could not be established."
    retryable = True


# --------------------------------------------------------------------------- #
# Value objects
# --------------------------------------------------------------------------- #
@dataclass
class LineStatus:
    """Live status of one SIM / voice line on a gateway."""

    line_id: str
    state: LineState = LineState.UNKNOWN
    phone_number: Optional[str] = None
    carrier: Optional[str] = None
    signal_percent: Optional[int] = None  # 0..100 when the hardware reports it
    registration_ok: bool = False
    active_channels: int = 0
    max_channels: Optional[int] = None
    sim_present: bool = True
    detail: Optional[str] = None
    checked_at: datetime = field(default_factory=_utcnow)

    @property
    def usable(self) -> bool:
        """A line is only usable when registered, SIM present and not PIN-locked."""
        return (
            self.sim_present
            and self.registration_ok
            and self.state == LineState.REGISTERED
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line_id": self.line_id,
            "state": self.state.value,
            "phone_number": self.phone_number,
            "carrier": self.carrier,
            "signal_percent": self.signal_percent,
            "registration_ok": self.registration_ok,
            "active_channels": self.active_channels,
            "max_channels": self.max_channels,
            "sim_present": self.sim_present,
            "usable": self.usable,
            "detail": self.detail,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class DeviceInfo:
    """A physical or logical gateway device discovered by an adapter."""

    device_id: str
    vendor: Optional[str] = None
    model: Optional[str] = None
    firmware: Optional[str] = None
    address: Optional[str] = None  # e.g. sip host:port
    lines: List[LineStatus] = field(default_factory=list)
    reachable: bool = False
    detail: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "vendor": self.vendor,
            "model": self.model,
            "firmware": self.firmware,
            "address": self.address,
            "reachable": self.reachable,
            "lines": [line.to_dict() for line in self.lines],
            "detail": self.detail,
        }


@dataclass
class ConnectivityResult:
    """Outcome of an explicit connectivity verification."""

    ok: bool
    latency_ms: Optional[float] = None
    message: str = ""
    detail: Optional[Dict[str, Any]] = None
    checked_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "latency_ms": self.latency_ms,
            "message": self.message,
            "detail": self.detail or {},
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class CallSnapshot:
    """Point-in-time view of a call as known by the adapter."""

    call_id: str
    state: CallState
    direction: Direction = Direction.INBOUND
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    line_id: Optional[str] = None
    channel: Optional[str] = None
    started_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    hangup_cause: Optional[HangupCause] = None
    transfer_target: Optional[str] = None
    audio_bridge_uri: Optional[str] = None
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        def _iso(v: Optional[datetime]) -> Optional[str]:
            return v.isoformat() if v else None

        return {
            "call_id": self.call_id,
            "state": self.state.value,
            "direction": self.direction.value,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "line_id": self.line_id,
            "channel": self.channel,
            "started_at": _iso(self.started_at),
            "answered_at": _iso(self.answered_at),
            "ended_at": _iso(self.ended_at),
            "hangup_cause": self.hangup_cause.value if self.hangup_cause else None,
            "transfer_target": self.transfer_target,
            "audio_bridge_uri": self.audio_bridge_uri,
            "failure_reason": self.failure_reason,
            "metadata": self.metadata,
        }


@dataclass
class InboundEvent:
    """Normalised inbound event emitted by a PBX/gateway toward the API layer."""

    event_type: str  # call_received, call_answered, call_ended, dtmf, error
    call_id: str
    from_number: Optional[str] = None
    to_number: Optional[str] = None
    line_id: Optional[str] = None
    channel: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    received_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "call_id": self.call_id,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "line_id": self.line_id,
            "channel": self.channel,
            "raw": self.raw,
            "received_at": self.received_at.isoformat(),
        }


@dataclass
class CapabilityReport:
    """What this adapter can and cannot do. Consumed by the UI and by policy gates."""

    provider: str
    discovery: Capability = Capability.UNKNOWN
    line_status: Capability = Capability.UNKNOWN
    connectivity_probe: Capability = Capability.UNKNOWN
    inbound_calls: Capability = Capability.UNKNOWN
    outbound_calls: Capability = Capability.UNKNOWN
    bidirectional_audio: Capability = Capability.UNKNOWN
    barge_in: Capability = Capability.UNKNOWN
    transfer: Capability = Capability.UNKNOWN
    reject_call: Capability = Capability.UNKNOWN
    recording: Capability = Capability.UNKNOWN
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "capabilities": {
                "discovery": self.discovery.value,
                "line_status": self.line_status.value,
                "connectivity_probe": self.connectivity_probe.value,
                "inbound_calls": self.inbound_calls.value,
                "outbound_calls": self.outbound_calls.value,
                "bidirectional_audio": self.bidirectional_audio.value,
                "barge_in": self.barge_in.value,
                "transfer": self.transfer.value,
                "reject_call": self.reject_call.value,
                "recording": self.recording.value,
            },
            "notes": self.notes,
        }

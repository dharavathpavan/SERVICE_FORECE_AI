"""
Telephony Adapter interface.

Every concrete adapter (mock, Asterisk/ARI, future SIP vendors) implements this
contract. The API/worker layers depend only on this interface.

Contract highlights:
  * Methods that a backend cannot support MUST raise ``NotSupportedError`` rather
    than silently no-op, and MUST be reflected in ``capabilities()``.
  * ``initiate_call`` / ``answer_call`` raise typed :class:`TelephonyError`
    subclasses on failure. They never return a fake success.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.services.telephony.types import (
    AudioBridgeError,
    CallSnapshot,
    CapabilityReport,
    ConnectivityResult,
    DeviceInfo,
    InboundEvent,
    LineStatus,
    NotSupportedError,
)


class TelephonyAdapter(ABC):
    """Abstract base class for all telephony providers."""

    #: Short machine identifier, e.g. ``"mock"`` or ``"asterisk"``.
    provider_name: str = "abstract"

    # ------------------------------------------------------------------ #
    # Capability advertisement
    # ------------------------------------------------------------------ #
    @abstractmethod
    def capabilities(self) -> CapabilityReport:
        """Report, honestly, what this adapter can do."""

    # ------------------------------------------------------------------ #
    # Discovery, line status, connectivity
    # ------------------------------------------------------------------ #
    @abstractmethod
    def discover_devices(self) -> List[DeviceInfo]:
        """Return the gateway devices this adapter can see.

        Adapters that cannot enumerate hardware return a single synthetic device
        describing the configured endpoint, with ``reachable`` reflecting a real probe.
        """

    @abstractmethod
    def get_line_status(self, line_id: Optional[str] = None) -> List[LineStatus]:
        """Return live SIM/line status. ``line_id=None`` returns all known lines."""

    @abstractmethod
    def verify_connectivity(self, device_id: Optional[str] = None) -> ConnectivityResult:
        """Actively probe the gateway/registration and report a real result."""

    # ------------------------------------------------------------------ #
    # Inbound call handling
    # ------------------------------------------------------------------ #
    @abstractmethod
    def parse_inbound_event(self, payload: Dict[str, Any]) -> InboundEvent:
        """Normalise a raw PBX/gateway webhook payload into an :class:`InboundEvent`.

        Raises :class:`TelephonyError` when the payload cannot be understood.
        """

    @abstractmethod
    def answer_call(self, call_id: str) -> CallSnapshot:
        """Answer a ringing inbound call. Raises on carrier/gateway failure."""

    @abstractmethod
    def reject_call(self, call_id: str, reason: str = "call_rejected") -> CallSnapshot:
        """Reject a ringing inbound call without answering."""

    # ------------------------------------------------------------------ #
    # Outbound calls
    # ------------------------------------------------------------------ #
    @abstractmethod
    def initiate_call(
        self,
        to_number: str,
        from_number: str,
        call_id: str,
        line_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CallSnapshot:
        """Originate an outbound call. Raises typed errors on failure."""

    # ------------------------------------------------------------------ #
    # Call lifecycle
    # ------------------------------------------------------------------ #
    @abstractmethod
    def get_call_state(self, call_id: str) -> CallSnapshot:
        """Return the current state of a call. Raises :class:`CallNotFoundError` if unknown."""

    @abstractmethod
    def hangup_call(self, call_id: str, cause: str = "normal_clearing") -> CallSnapshot:
        """Terminate a call."""

    @abstractmethod
    def transfer_call(self, call_id: str, target: str) -> CallSnapshot:
        """Transfer an in-progress call to a human destination (SIP URI or E.164)."""

    # ------------------------------------------------------------------ #
    # Audio
    # ------------------------------------------------------------------ #
    @abstractmethod
    def bridge_audio(self, call_id: str) -> str:
        """Attach the call's media to the AI audio bridge.

        Returns the bridge URI (AudioSocket/WebSocket endpoint) the voice session
        should connect to. Raises :class:`AudioBridgeError` on failure.
        """

    # ------------------------------------------------------------------ #
    # Convenience
    # ------------------------------------------------------------------ #
    def health(self) -> Dict[str, Any]:
        """Lightweight, non-throwing health summary for /health and the dashboard."""
        try:
            caps = self.capabilities()
            conn = self.verify_connectivity()
            return {
                "provider": self.provider_name,
                "reachable": conn.ok,
                "latency_ms": conn.latency_ms,
                "message": conn.message,
                "capabilities": caps.to_dict(),
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "provider": self.provider_name,
                "reachable": False,
                "message": f"{type(exc).__name__}: {exc}",
            }

    # Helper for subclasses to signal an unsupported operation uniformly.
    @staticmethod
    def _unsupported(operation: str) -> "NotSupportedError":
        return NotSupportedError(
            f"{operation} is not supported by this telephony adapter.",
            details={"operation": operation},
        )

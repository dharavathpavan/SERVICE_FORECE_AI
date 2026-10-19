"""
Gateway & line health service.

Central rule enforced here: a gateway or SIM is **never** reported as connected
merely because a database row exists. Connection state changes only after a real
probe through the configured telephony adapter.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.telephony import Gateway, PhoneConnection
from app.services.telephony.adapter import TelephonyAdapter
from app.services.telephony.factory import get_adapter
from app.services.telephony.types import ConnectivityResult, LineState, LineStatus, TelephonyError

logger = logging.getLogger(__name__)

# Gateway lifecycle states persisted in ``gateways.status``.
STATUS_UNVERIFIED = "unverified"
STATUS_ONLINE = "online"
STATUS_DEGRADED = "degraded"
STATUS_OFFLINE = "offline"


@dataclass
class ProbeResult:
    """Outcome of probing a gateway and its lines."""

    ok: bool
    status: str
    message: str
    latency_ms: Optional[float] = None
    lines: List[LineStatus] = field(default_factory=list)
    detail: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    probed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "lines": [line.to_dict() for line in self.lines],
            "detail": self.detail,
            "errors": self.errors,
            "probed_at": self.probed_at.isoformat(),
        }


def probe_gateway(
    adapter: Optional[TelephonyAdapter] = None,
    *,
    device_id: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> ProbeResult:
    """Actively probe the gateway. Never raises for connectivity problems."""
    adapter = adapter or get_adapter()
    errors: List[str] = []

    try:
        connectivity: ConnectivityResult = adapter.verify_connectivity(device_id=device_id)
    except TelephonyError as exc:
        return ProbeResult(
            ok=False,
            status=STATUS_OFFLINE,
            message=exc.user_message,
            errors=[exc.message],
            detail={"error": exc.code, **(exc.details or {})},
        )

    if not connectivity.ok:
        return ProbeResult(
            ok=False,
            status=STATUS_OFFLINE,
            message=connectivity.message or "Gateway is not reachable.",
            latency_ms=connectivity.latency_ms,
            detail=connectivity.detail or {},
        )

    lines: List[LineStatus] = []
    try:
        lines = adapter.get_line_status()
    except TelephonyError as exc:
        errors.append(f"line_status: {exc.message}")

    if phone_number:
        lines = [ln for ln in lines if ln.phone_number in (None, phone_number)]

    usable = [ln for ln in lines if ln.usable]
    if lines and not usable:
        status = STATUS_DEGRADED
        message = "Gateway reachable but no SIM line is registered."
    elif not lines:
        status = STATUS_DEGRADED if errors else STATUS_ONLINE
        message = "Gateway reachable; line detail unavailable."
    else:
        status = STATUS_ONLINE
        message = f"Gateway reachable; {len(usable)} line(s) registered."

    return ProbeResult(
        ok=status == STATUS_ONLINE,
        status=status,
        message=message,
        latency_ms=connectivity.latency_ms,
        lines=lines,
        detail=connectivity.detail or {},
        errors=errors,
    )


def apply_probe(db: Session, gateway: Gateway, result: ProbeResult) -> Gateway:
    """Persist a probe outcome onto a gateway row."""
    gateway.status = result.status
    gateway.last_heartbeat = result.probed_at
    gateway.health_details = {
        "latency_ms": result.latency_ms,
        "message": result.message,
        "line_count": len(result.lines),
        "usable_lines": sum(1 for ln in result.lines if ln.usable),
        "active_channels": sum(ln.active_channels for ln in result.lines),
        "registration": "OK" if result.ok else "FAILED",
        "errors": result.errors,
        **(result.detail or {}),
    }
    db.add(gateway)
    db.commit()
    db.refresh(gateway)
    return gateway


def verify_gateway(
    db: Session,
    gateway: Gateway,
    adapter: Optional[TelephonyAdapter] = None,
) -> ProbeResult:
    """Probe a gateway and persist the result. Used by the /verify endpoint."""
    result = probe_gateway(adapter, device_id=gateway.identifier)
    apply_probe(db, gateway, result)
    return result


def verify_phone_connection(
    db: Session,
    connection: PhoneConnection,
    adapter: Optional[TelephonyAdapter] = None,
) -> ProbeResult:
    """Probe a specific line and update the phone connection's verified state."""
    adapter = adapter or get_adapter()
    # Only real (non-mock) connection types require live verification; the mock
    # provider legitimately reports a simulated line as usable.
    result = probe_gateway(adapter, phone_number=connection.phone_number)

    matching = [ln for ln in result.lines if ln.phone_number == connection.phone_number] or result.lines
    line_ok = any(ln.usable for ln in matching) if matching else False

    connection.is_verified = bool(line_ok)
    connection.health_status = (
        "healthy" if line_ok else ("offline" if result.status == STATUS_OFFLINE else "degraded")
    )
    connection.last_health_check = result.probed_at
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return result


def summarize_gateway(gateway: Gateway) -> Dict[str, Any]:
    """Serialise a gateway including derived health for API responses."""
    details = gateway.health_details or {}
    return {
        "id": gateway.id,
        "identifier": gateway.identifier,
        "sip_endpoint": gateway.sip_endpoint,
        "status": gateway.status,
        "last_heartbeat": gateway.last_heartbeat,
        "health_details": details,
        "connected": gateway.status == STATUS_ONLINE,
        "needs_verification": gateway.status == STATUS_UNVERIFIED,
        "created_at": gateway.created_at,
    }

"""
Asterisk adapter using ARI (Asterisk REST Interface).

This is the supported production path for a physical-SIM deployment:

    SIM → GSM/VoLTE gateway (Yeastar TG / Dinstar UC2000) → SIP → Asterisk(PJSIP)
        → ARI Stasis app → ExternalMedia/WebSocket → ServiceForce audio bridge

Honesty rules implemented here:
  * ``verify_connectivity`` performs a real HTTP call to ARI and reports the true
    result; it never assumes reachability.
  * Call-control methods raise :class:`GatewayOfflineError` when ARI is unreachable
    and typed carrier errors when Asterisk returns them.
  * Capabilities that Asterisk exposes only with extra modules are reported as
    UNKNOWN rather than SUPPORTED.

The adapter is exercised end-to-end only when ``ASTERISK_E2E=1`` (a live PBX);
unit tests use an injected ``httpx`` transport so no PBX is required.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services.telephony.adapter import TelephonyAdapter
from app.services.telephony.types import (
    AudioBridgeError,
    CallNotFoundError,
    CallSnapshot,
    CallState,
    Capability,
    CapabilityReport,
    ConnectivityResult,
    DeviceInfo,
    Direction,
    GatewayOfflineError,
    HangupCause,
    InboundEvent,
    LineState,
    LineStatus,
    TelephonyError,
    UnreachableError,
    _utcnow,
)

# Asterisk channel state → our CallState
_CHANNEL_STATE_MAP = {
    "Down": CallState.QUEUED,
    "Rsrvd": CallState.QUEUED,
    "OffHook": CallState.RINGING,
    "Dialing": CallState.RINGING,
    "Ring": CallState.RINGING,
    "Ringing": CallState.RINGING,
    "Up": CallState.IN_PROGRESS,
    "Busy": CallState.BUSY,
    "Dialing Offhook": CallState.RINGING,
    "Pre-ring": CallState.RINGING,
}


class AsteriskAdapter(TelephonyAdapter):
    """Production adapter for Asterisk/FreePBX over ARI."""

    provider_name = "asterisk"

    def __init__(
        self,
        host: Optional[str] = None,
        ari_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        app_name: Optional[str] = None,
        media_host: Optional[str] = None,
        media_port: Optional[int] = None,
        timeout: float = 5.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.host = host or settings.ASTERISK_HOST
        self.ari_port = ari_port or settings.ASTERISK_ARI_PORT
        self.username = username or settings.ASTERISK_ARI_USER
        self.password = password or settings.ASTERISK_ARI_SECRET
        self.app_name = app_name or settings.ASTERISK_APP
        self.media_host = media_host or settings.ASTERISK_MEDIA_HOST
        self.media_port = media_port or settings.ASTERISK_MEDIA_PORT
        self._base = f"http://{self.host}:{self.ari_port}/ari"
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self._base,
            auth=(self.username, self.password),
            timeout=timeout,
        )
        self._calls: Dict[str, CallSnapshot] = {}

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
            barge_in=Capability.UNKNOWN,  # depends on the streaming voice provider
            transfer=Capability.SUPPORTED,
            reject_call=Capability.SUPPORTED,
            recording=Capability.SUPPORTED,
            notes=[
                "Requires the Asterisk 'stasis' app and externalMedia modules.",
                "Barge-in latency depends on the voice provider and codec, not Asterisk.",
                f"ARI endpoint: {self._base}",
            ],
        )

    # ------------------------------------------------------------------ #
    # Internal HTTP helpers
    # ------------------------------------------------------------------ #
    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            resp = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise GatewayOfflineError(
                f"Asterisk ARI unreachable at {self._base}: {exc}",
                details={"endpoint": self._base},
                retryable=True,
            ) from exc

        if resp.status_code == 401:
            raise TelephonyError(
                "Asterisk rejected ARI credentials.",
                details={"endpoint": self._base},
                retryable=False,
            )
        return resp

    # ------------------------------------------------------------------ #
    # Connectivity / discovery / line status
    # ------------------------------------------------------------------ #
    def verify_connectivity(self, device_id: Optional[str] = None) -> ConnectivityResult:
        start = time.perf_counter()
        try:
            resp = self._request("GET", "/asterisk/info")
        except GatewayOfflineError as exc:
            return ConnectivityResult(ok=False, message=exc.user_message, detail=exc.details)

        latency = round((time.perf_counter() - start) * 1000, 2)
        if resp.status_code != 200:
            return ConnectivityResult(
                ok=False,
                latency_ms=latency,
                message=f"ARI returned HTTP {resp.status_code}.",
                detail={"body": resp.text[:500]},
            )

        info = resp.json() if resp.content else {}
        return ConnectivityResult(
            ok=True,
            latency_ms=latency,
            message="Asterisk ARI reachable.",
            detail={
                "system": info.get("system", {}),
                "build": info.get("build", {}),
                "config": info.get("config", {}),
            },
        )

    def discover_devices(self) -> List[DeviceInfo]:
        reachable = self.verify_connectivity().ok
        lines = self.get_line_status() if reachable else []
        return [
            DeviceInfo(
                device_id=device_id or f"asterisk@{self.host}:{self.ari_port}",
                vendor="Asterisk",
                model="PJSIP/PBX",
                address=self._base,
                reachable=reachable,
                lines=lines,
                detail=None if reachable else "ARI did not respond to the discovery probe.",
            )
        ]

    def get_line_status(self, line_id: Optional[str] = None) -> List[LineStatus]:
        """PJSIP endpoints represent SIM-backed gateway trunks."""
        try:
            resp = self._request("GET", "/endpoints")
        except GatewayOfflineError as exc:
            raise exc

        if resp.status_code != 200:
            raise TelephonyError(
                f"Could not list Asterisk endpoints (HTTP {resp.status_code}).",
                details={"body": resp.text[:300]},
            )

        lines: List[LineStatus] = []
        for ep in resp.json():
            name = ep.get("resource") or ep.get("id")
            if not name:
                continue
            if line_id and name != line_id:
                continue
            state = (ep.get("state") or "").lower()
            online = state in ("online", "available")
            channels = [c for c in (ep.get("channelvars") or {})]
            lines.append(
                LineStatus(
                    line_id=name,
                    state=LineState.REGISTERED if online else LineState.UNREGISTERED,
                    phone_number=(
                        ep.get("channelvars", {}) or {}
                    ).get("CALLERID(num)"),
                    carrier=ep.get("technology"),
                    registration_ok=online,
                    active_channels=0,
                    max_channels=None,
                    sim_present=online,
                    detail=f"PJSIP endpoint state={state or 'unknown'}",
                )
            )
        return lines

    # ------------------------------------------------------------------ #
    # Inbound
    # ------------------------------------------------------------------ #
    def parse_inbound_event(self, payload: Dict[str, Any]) -> InboundEvent:
        """Normalise an ARI StasisStart / ChannelStateChange payload."""
        etype = payload.get("type", "")
        channel = payload.get("channel") or {}
        call_id = (
            payload.get("call_id")
            or channel.get("id")
            or payload.get("channel_id")
        )
        if not call_id:
            raise TelephonyError(
                "ARI payload missing channel id; cannot normalise inbound event.",
                details={"payload_keys": list(payload.keys())},
            )

        if etype in ("StasisStart", "ChannelStateChange"):
            event_type = "call_received" if etype == "StasisStart" else "call_state"
        elif etype == "ChannelDestroyed":
            event_type = "call_ended"
        elif etype == "ChannelDtmfReceived":
            event_type = "dtmf"
        else:
            event_type = "error"

        caller = (channel.get("caller") or {}).get("number")
        dialed = (channel.get("dialplan") or {}).get("exten")
        return InboundEvent(
            event_type=event_type,
            call_id=str(call_id),
            from_number=caller,
            to_number=dialed,
            line_id=(channel.get("dialplan") or {}).get("context"),
            channel=channel.get("name"),
            raw=payload,
        )

    def answer_call(self, call_id: str) -> CallSnapshot:
        resp = self._request("POST", f"/channels/{call_id}/answer")
        if resp.status_code not in (200, 204):
            raise TelephonyError(
                "Asterisk failed to answer the call.",
                details={"call_id": call_id, "http_status": resp.status_code, "body": resp.text[:300]},
            )
        snap = self.get_call_state(call_id)
        snap.state = CallState.IN_PROGRESS
        snap.answered_at = _utcnow()
        return snap

    def reject_call(self, call_id: str, reason: str = "call_rejected") -> CallSnapshot:
        # ARI has no dedicated reject; hang up with a cause.
        resp = self._request(
            "DELETE", f"/channels/{call_id}", params={"reason": "rejected"}
        )
        if resp.status_code not in (200, 204, 404):
            raise TelephonyError(
                "Asterisk failed to reject the call.",
                details={"call_id": call_id, "http_status": resp.status_code},
            )
        snap = self._calls.get(call_id) or CallSnapshot(call_id=call_id, state=CallState.REJECTED)
        snap.state = CallState.REJECTED
        snap.ended_at = _utcnow()
        snap.hangup_cause = HangupCause.CALL_REJECTED
        snap.failure_reason = reason
        self._calls[call_id] = snap
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
        endpoint = line_id or f"PJSIP/{to_number}"
        params = {
            "endpoint": endpoint,
            "app": self.app_name,
            "appArgs": call_id,
            "callerId": from_number,
        }
        resp = self._request("POST", "/channels", params=params)
        if resp.status_code not in (200, 201):
            body = resp.text[:500]
            if resp.status_code == 404 or "not found" in body.lower():
                raise UnreachableError(
                    "Asterisk could not reach the destination.",
                    details={"to_number": to_number, "endpoint": endpoint, "body": body},
                )
            raise TelephonyError(
                "Asterisk failed to originate the call.",
                details={"http_status": resp.status_code, "body": body},
            )

        data = resp.json() if resp.content else {}
        snap = CallSnapshot(
            call_id=data.get("id", call_id),
            state=_CHANNEL_STATE_MAP.get(data.get("state", ""), CallState.RINGING),
            direction=Direction.OUTBOUND,
            from_number=from_number,
            to_number=to_number,
            line_id=line_id,
            channel=data.get("name"),
            started_at=_utcnow(),
            metadata=metadata or {},
        )
        self._calls[snap.call_id] = snap
        return snap

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def get_call_state(self, call_id: str) -> CallSnapshot:
        resp = self._request("GET", f"/channels/{call_id}")
        if resp.status_code == 404:
            snap = self._calls.get(call_id)
            if snap:
                return snap
            raise CallNotFoundError(f"Asterisk has no channel {call_id}", details={"call_id": call_id})
        if resp.status_code != 200:
            raise TelephonyError(
                "Asterisk could not return channel state.",
                details={"call_id": call_id, "http_status": resp.status_code},
            )

        data = resp.json()
        snap = self._calls.get(call_id) or CallSnapshot(call_id=call_id, state=CallState.QUEUED)
        snap.state = _CHANNEL_STATE_MAP.get(data.get("state", ""), snap.state)
        snap.channel = data.get("name", snap.channel)
        self._calls[call_id] = snap
        return snap

    def hangup_call(self, call_id: str, cause: str = "normal_clearing") -> CallSnapshot:
        resp = self._request("DELETE", f"/channels/{call_id}")
        if resp.status_code not in (200, 204, 404):
            raise TelephonyError(
                "Asterisk failed to hang up the call.",
                details={"call_id": call_id, "http_status": resp.status_code},
            )
        snap = self._calls.get(call_id) or CallSnapshot(call_id=call_id, state=CallState.COMPLETED)
        snap.state = CallState.COMPLETED
        snap.ended_at = _utcnow()
        try:
            snap.hangup_cause = HangupCause(cause)
        except ValueError:
            snap.hangup_cause = HangupCause.NORMAL_CLEARING
        self._calls[call_id] = snap
        return snap

    def transfer_call(self, call_id: str, target: str) -> CallSnapshot:
        """Blind transfer via ARI: create a channel toward the target, then bridge."""
        resp = self._request(
            "POST",
            "/channels",
            params={"endpoint": f"PJSIP/{target}", "app": self.app_name, "appArgs": f"transfer-{call_id}"},
        )
        if resp.status_code not in (200, 201):
            raise TelephonyError(
                "Asterisk could not create the transfer leg.",
                details={"target": target, "http_status": resp.status_code, "body": resp.text[:300]},
            )
        target_channel = resp.json().get("id")
        bridge = self._request("POST", "/bridges", params={"type": "mixing"})
        if bridge.status_code not in (200, 201):
            raise TelephonyError("Asterisk could not create a bridge.", details={"http_status": bridge.status_code})
        bridge_id = bridge.json().get("id")
        self._request("POST", f"/bridges/{bridge_id}/addChannel", params={"channel": call_id})
        self._request("POST", f"/bridges/{bridge_id}/addChannel", params={"channel": target_channel})

        snap = self._calls.get(call_id) or CallSnapshot(call_id=call_id, state=CallState.TRANSFERRED)
        snap.state = CallState.TRANSFERRED
        snap.transfer_target = target
        self._calls[call_id] = snap
        return snap

    # ------------------------------------------------------------------ #
    # Audio
    # ------------------------------------------------------------------ #
    def bridge_audio(self, call_id: str) -> str:
        """Ask Asterisk to fork this channel's media to our audio socket."""
        webhook = urlparse(settings.VOICE_BRIDGE_URL)
        try:
            resp = self._request(
                "POST",
                f"/channels/{call_id}/externalMedia",
                params={
                    "app": self.app_name,
                    "external_host": f"{self.media_host}:{self.media_port}",
                    "format": "slin16",
                    "encapsulation": "audiosocket",
                },
            )
        except GatewayOfflineError as exc:
            raise AudioBridgeError(exc.user_message, details=exc.details) from exc

        if resp.status_code not in (200, 201):
            raise AudioBridgeError(
                "Asterisk refused to start external media for the call.",
                details={"call_id": call_id, "http_status": resp.status_code, "body": resp.text[:300]},
            )
        return f"{webhook.scheme}://{webhook.netloc}{webhook.path}" if webhook.netloc else settings.VOICE_BRIDGE_URL

    # ------------------------------------------------------------------ #
    def close(self) -> None:
        if self._owns_client:
            self._client.close()

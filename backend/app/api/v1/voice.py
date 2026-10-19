"""
Voice/inbound telephony entrypoints.

  * ``POST /telephony/inbound`` — webhook the PBX/gateway bridge calls when a call
    arrives. Not JWT-authenticated (the PBX is the caller); protected by an HMAC
    signature when ``WEBHOOK_REQUIRE_SIGNATURE`` is on.
  * ``WS /ws/calls/{call_id}`` — live status/transcript stream for the dashboard.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.telephony import PhoneConnection
from app.models.tenant import Organization, User, OrganizationMembership
from app.models.call import Call
from app.services.calls.events import event_hub
from app.services.calls.session_service import CallSessionService
from app.services.telephony.factory import get_adapter
from app.services.telephony.types import TelephonyError
from app.services.voice.factory import get_voice_provider
from app.services.voice.provider import VoiceEventType, VoiceProviderError
from app.services.voice.session_config import build_voice_config
from app.services.voice.synthesis import decode_audio

router = APIRouter(prefix="", tags=["Voice & Inbound"])
logger = logging.getLogger(__name__)


def _verify_signature(raw_body: bytes, signature: Optional[str]) -> None:
    if not settings.WEBHOOK_REQUIRE_SIGNATURE:
        return
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")
    expected = hmac.new(
        settings.WEBHOOK_SIGNING_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")


@router.post("/telephony/inbound")
async def inbound_call_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    db: Session = Depends(get_db),
):
    """
    Accepts an inbound call event from the PBX/gateway and runs the inbound workflow.

    Always returns 200 with an honest ``action`` so the bridge can act. A malformed
    payload returns 400 (the bridge should not retry forever).
    """
    raw = await request.body()
    _verify_signature(raw, x_signature)

    try:
        payload = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON payload")

    adapter = get_adapter()
    try:
        event = adapter.parse_inbound_event(payload)
    except TelephonyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.user_message)

    # Resolve the tenant from the dialed number (DID).
    connection = (
        db.query(PhoneConnection)
        .filter(PhoneConnection.phone_number == event.to_number)
        .first()
    )
    if not connection:
        logger.warning("Inbound call to unknown number %s", event.to_number)
        return {
            "action": "rejected",
            "message": "This number is not provisioned in ServiceForce.ai.",
            "call_id": event.call_id,
        }

    organization = (
        db.query(Organization)
        .filter(Organization.id == connection.organization_id, Organization.is_active.is_(True))
        .first()
    )
    if not organization:
        return {
            "action": "rejected",
            "message": "Workspace is inactive.",
            "call_id": event.call_id,
        }

    service = CallSessionService(db, adapter=adapter)
    outcome = service.handle_inbound(organization, event)
    return {"organization_id": organization.id, **outcome.to_dict()}


def _authorize_ws(db: Session, token: str, call: Call) -> Optional[str]:
    """
    Minimal WebSocket auth: decode the JWT and confirm the user belongs to the
    call's organization. Returns the user id or ``None``.
    """
    import jwt  # local import keeps cold-start light

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        return None
    membership = (
        db.query(OrganizationMembership)
        .filter(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == call.organization_id,
        )
        .first()
    )
    return user.id if membership else None


@router.websocket("/ws/calls/{call_id}")
async def call_stream(websocket: WebSocket, call_id: str, db: Session = Depends(get_db)):
    """
    Streams live call events. The client passes a bearer token via the ``token``
    query parameter (browsers cannot set headers on WebSocket handshakes).
    """
    token = websocket.query_params.get("token", "")
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        await websocket.close(code=4404)
        return
    if not _authorize_ws(db, token, call):
        await websocket.close(code=4401)
        return

    await websocket.accept()
    queue = event_hub.subscribe(call_id)
    try:
        # Replay history so a late subscriber is not blind.
        for past in event_hub.history(call_id):
            await websocket.send_json({"replay": True, **past})
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        event_hub.unsubscribe(call_id, queue)


@router.get("/voice/capabilities")
def voice_capabilities():
    """Reports the configured real-time voice provider and what it supports."""
    provider = get_voice_provider()
    return provider.capabilities()


@router.websocket("/voice/stream")
async def voice_audio_stream(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    Audio bridge endpoint the PBX/gateway connects to for a live call.

    The gateway sends binary PCM16 frames; the backend forwards them to the voice
    session and returns model audio plus transcript/tool events as JSON.
    """
    call_id = websocket.query_params.get("call_id")
    token = websocket.query_params.get("token", "")
    if not call_id:
        await websocket.close(code=4400)
        return

    call = db.query(Call).filter(Call.id == call_id).first()
    if not call or not _authorize_ws(db, token, call):
        await websocket.close(code=4401)
        return

    provider = get_voice_provider()
    # The session speaks with the agent configured on this call - its prompt,
    # greeting, voice, language and enabled tools - rather than a fixed script.
    config = build_voice_config(db, call)
    try:
        session = provider.create_session(config)
    except VoiceProviderError as exc:
        await websocket.accept()
        await websocket.send_json({"type": "error", **exc.to_dict()})
        await websocket.close(code=1011)
        return

    await websocket.accept()
    await session.start()

    service = CallSessionService(db)
    started_at = time.monotonic()
    last_turn_ms = 0
    # Audio the provider generated for the AI's own turns, in emission order. Kept so
    # the dashboard can play back what the agent said; it is the agent side only.
    captured = bytearray()
    capture_rate = 0

    def _record_turn(data: Dict[str, Any]) -> None:
        """Persist a finished transcript turn so the call keeps a real record."""
        nonlocal last_turn_ms
        if data.get("final") is False:
            return
        text = str(data.get("text") or "").strip()
        if not text:
            return
        now_ms = int((time.monotonic() - started_at) * 1000)
        try:
            service.add_transcript_turn(
                call,
                str(data.get("speaker") or "system"),
                text,
                last_turn_ms,
                now_ms,
            )
        except Exception:  # never drop the audio bridge over a transcript write
            logger.exception("Could not persist transcript turn for call %s", call_id)
        last_turn_ms = now_ms

    def _capture_audio(data: Dict[str, Any]) -> None:
        """Accumulate provider audio; never let a decode problem break the bridge."""
        nonlocal capture_rate
        try:
            pcm, rate = decode_audio(data)
        except Exception:
            logger.exception("Could not read AUDIO_OUT payload for call %s", call_id)
            return
        if not pcm:
            return
        captured.extend(pcm)
        capture_rate = capture_rate or rate

    def _audio_engine() -> Optional[str]:
        try:
            caps = provider.capabilities() or {}
        except Exception:
            return None
        report = caps.get("audio_engine") or {}
        return report.get("engine") or caps.get("provider")

    async def pump_provider() -> None:
        while True:
            event = await session.receive()
            if event.type == VoiceEventType.AUDIO_OUT:
                _capture_audio(event.data)
            await websocket.send_json(event.to_dict())
            if event.type == VoiceEventType.TRANSCRIPT:
                _record_turn(event.data)
            if event.type.value == "end":
                break

    pump = asyncio.create_task(pump_provider())
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            data = message.get("bytes")
            if data:
                await session.send_audio(data)
    except WebSocketDisconnect:
        pass
    finally:
        pump.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await pump
        if captured:
            try:
                service.store_agent_audio(
                    call, bytes(captured), capture_rate or settings.VOICE_OUTPUT_SAMPLE_RATE, engine=_audio_engine()
                )
            except Exception:  # an artifact failure must not surface as a call failure
                logger.exception("Could not store agent audio for call %s", call_id)
        await session.end()

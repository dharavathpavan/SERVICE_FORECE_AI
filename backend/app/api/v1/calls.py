import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_role, TenantContext
from app.models.tenant import OrgRole, AuditLog
from app.models.call import Call, CallEvent, Transcript
from app.models.agent import Agent
from app.models.billing import UsageRecord
from app.services.telephony.mock_adapter import mock_telephony
from app.services.telephony.factory import get_adapter
from app.services.calls.session_service import CallSessionService
from app.models.telephony import PhoneConnection

router = APIRouter(prefix="/calls", tags=["Call Management"])


class CallSimulateRequest(BaseModel):
    agent_id: Optional[str] = None
    scenario: str = "order_tracking"  # order_tracking, appointment_booking, human_escalation, faq_inquiry
    caller_phone: str = "+1-555-0199"
    direction: str = "inbound"


class OutboundCallRequest(BaseModel):
    to_number: str
    connection_id: Optional[str] = None
    agent_id: Optional[str] = None
    reason: Optional[str] = None
    confirmed: bool = False
    metadata: Optional[dict] = None


@router.get("")
def list_calls(
    agent_id: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Lists calls for the organization with pagination and multi-column filtering."""
    q = db.query(Call).filter(Call.organization_id == ctx.organization_id)
    if agent_id:
        q = q.filter(Call.agent_id == agent_id)
    if direction:
        q = q.filter(Call.direction == direction)
    if status:
        q = q.filter(Call.status == status)
    if outcome:
        q = q.filter(Call.outcome == outcome)

    total = q.count()
    calls = q.order_by(Call.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": c.id,
                "agent_id": c.agent_id,
                "phone_number": c.phone_number,
                "caller_id": c.caller_id,
                "direction": c.direction,
                "status": c.status,
                "outcome": c.outcome,
                "start_time": c.start_time,
                "end_time": c.end_time,
                "duration_seconds": c.duration_seconds,
                "summary": c.summary,
                "estimated_cost": c.estimated_cost,
                "created_at": c.created_at,
            }
            for c in calls
        ]
    }


@router.get("/{call_id}")
def get_call_details(
    call_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Retrieves comprehensive call record with event timeline, multi-turn transcript, and summary."""
    call = db.query(Call).filter(
        Call.id == call_id,
        Call.organization_id == ctx.organization_id
    ).first()

    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call record not found")

    events = db.query(CallEvent).filter(CallEvent.call_id == call.id).order_by(CallEvent.created_at.asc()).all()
    transcripts = db.query(Transcript).filter(Transcript.call_id == call.id).order_by(Transcript.start_timestamp_ms.asc()).all()

    return {
        "id": call.id,
        "organization_id": call.organization_id,
        "agent_id": call.agent_id,
        "phone_number": call.phone_number,
        "caller_id": call.caller_id,
        "direction": call.direction,
        "status": call.status,
        "outcome": call.outcome,
        "start_time": call.start_time,
        "end_time": call.end_time,
        "duration_seconds": call.duration_seconds,
        "failure_reason": call.failure_reason,
        "summary": call.summary,
        "recording_url": call.recording_url,
        "agent_audio_url": f"/api/v1/calls/{call.id}/agent-audio" if call.agent_audio_key else None,
        "estimated_cost": call.estimated_cost,
        "created_at": call.created_at,
        "events": [
            {"id": e.id, "event_type": e.event_type, "payload": e.payload, "created_at": e.created_at}
            for e in events
        ],
        "transcripts": [
            {
                "id": t.id,
                "speaker": t.speaker,
                "text": t.text,
                "start_timestamp_ms": t.start_timestamp_ms,
                "end_timestamp_ms": t.end_timestamp_ms,
                "confidence": t.confidence,
            }
            for t in transcripts
        ]
    }


@router.get("/{call_id}/agent-audio")
def get_agent_audio(
    call_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Streams the audio the AI produced on this call.

    This is the **agent side only** - audio the voice provider generated for the AI's
    own turns. It is not a carrier recording: if the gateway records both parties the
    adapter stores that separately under ``recording_url``. Bytes are served from
    private storage through this authenticated, organization-scoped endpoint rather
    than a public URL.
    """
    call = db.query(Call).filter(
        Call.id == call_id,
        Call.organization_id == ctx.organization_id,
    ).first()
    if not call:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call record not found")
    if not call.agent_audio_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This call has no stored agent audio.",
        )

    from app.services.storage import ObjectNotFound, get_storage

    try:
        data = get_storage().get(call.agent_audio_key)
    except ObjectNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent audio is no longer available in storage.",
        )

    return Response(
        content=data,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'inline; filename="call-{call.id}-agent.wav"',
            "Cache-Control": "private, no-store",
        },
    )


@router.post("/simulate")
def simulate_call_lifecycle(
    req: CallSimulateRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Executes an end-to-end simulated call with realistic telephony state changes,
    barge-in interruption, tool calls, transcript logs, and summary generation.
    """
    agent = None
    if req.agent_id:
        agent = db.query(Agent).filter(Agent.id == req.agent_id, Agent.organization_id == ctx.organization_id).first()
    if not agent:
        agent = db.query(Agent).filter(Agent.organization_id == ctx.organization_id).first()

    now = datetime.now(timezone.utc)
    duration = 145 if req.scenario != "human_escalation" else 62
    start_time = now - timedelta(seconds=duration)
    end_time = now

    outcome = "ai_resolved"
    summary = "Customer called to inquire about order status. Agent looked up tracking and confirmed delivery ETA for tomorrow."
    
    if req.scenario == "appointment_booking":
        summary = "Customer scheduled a specialist consultation for tomorrow at 10:00 AM. Appointment APT-6721 confirmed."
    elif req.scenario == "human_escalation":
        outcome = "human_transferred"
        summary = "Customer requested human escalation regarding billing dispute. Agent transferred caller to senior supervisor queue."
    elif req.scenario == "faq_inquiry":
        summary = "Customer inquired about warranty and return policy. Agent answered using knowledge base reference."

    # 1. Create Call
    call = Call(
        organization_id=ctx.organization_id,
        agent_id=agent.id if agent else None,
        phone_number=req.caller_phone,
        caller_id=f"Apex-{ctx.organization.name[:6].upper()}",
        direction=req.direction,
        status="completed" if outcome != "human_transferred" else "transferred",
        outcome=outcome,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration,
        summary=summary,
        estimated_cost=round((duration / 60.0) * 0.035, 4),
    )
    db.add(call)
    db.flush()

    # 2. Add Call Events
    events_data = [
        ("speech_start", {"speaker": "agent", "message": "Greeting initial packet streamed"}),
        ("speech_end", {"speaker": "agent", "turn": 1}),
        ("speech_start", {"speaker": "caller", "intent": req.scenario}),
        ("speech_end", {"speaker": "caller", "turn": 2}),
    ]

    if req.scenario == "order_tracking":
        events_data.append(("tool_call", {"tool": "get_order_status", "order_id": "ORD-8921", "result": "Shipped via FedEx"}))
    elif req.scenario == "appointment_booking":
        events_data.append(("tool_call", {"tool": "get_appointment_availability", "date": "tomorrow"}))
        events_data.append(("tool_call", {"tool": "create_appointment", "code": "APT-6721"}))
    elif req.scenario == "human_escalation":
        events_data.append(("barge_in", {"detected_latency_ms": 190, "action": "abort_agent_speech"}))
        events_data.append(("transfer_request", {"target": "+1-800-HUMAN", "queue": "escalations"}))

    events_data.append(("call_completed", {"disposition": outcome, "total_seconds": duration}))

    for etype, payload in events_data:
        db.add(CallEvent(call_id=call.id, event_type=etype, payload=payload))

    # 3. Add Transcripts
    if req.scenario == "order_tracking":
        transcript_lines = [
            ("agent", agent.greeting if agent else "Hello! Thank you for calling. How can I assist you today?", 0, 3200),
            ("caller", "Hi, I placed an order yesterday and wanted to know when it will be delivered.", 3800, 7100),
            ("agent", "I'd be glad to check that for you! May I please have your order number or the phone number associated with the account?", 7500, 12400),
            ("caller", "The order number is ORD-8921.", 13000, 15600),
            ("agent", "Thank you. Let me check the real-time carrier status for order ORD-8921... I see it has shipped via FedEx Priority and is scheduled for delivery tomorrow by 2:00 PM.", 16000, 24500),
            ("caller", "That's fantastic news. Thank you so much!", 25200, 27300),
            ("agent", "You're very welcome! Is there anything else I can help you with today?", 27800, 31000),
            ("caller", "No, that's everything. Have a great day!", 31500, 33500),
            ("agent", "Thank you for calling. Have a wonderful day! Goodbye.", 34000, 37000),
        ]
    elif req.scenario == "appointment_booking":
        transcript_lines = [
            ("agent", agent.greeting if agent else "Thank you for calling. How may I help you?", 0, 3000),
            ("caller", "Hello, I would like to schedule a consultation with a specialist for tomorrow.", 3500, 7200),
            ("agent", "I can certainly help you book that. We have available slots tomorrow at 10:00 AM, 2:30 PM, and 4:15 PM. Do any of those work for you?", 7800, 14200),
            ("caller", "10:00 AM works perfectly.", 14800, 16500),
            ("agent", "Great! I have reserved 10:00 AM tomorrow for your consultation. Your confirmation code is APT-6721. You'll receive an SMS confirmation shortly.", 17000, 24000),
            ("caller", "Awesome, thank you!", 24500, 26000),
        ]
    else:
        transcript_lines = [
            ("agent", "Hello! How can I help you today?", 0, 2500),
            ("caller", "I have an urgent billing dispute that I need to speak with a human manager about immediately.", 3000, 7500),
            ("agent", "I completely understand. Let me transfer you directly to our supervisor queue right now. Please hold for just a few seconds.", 8000, 14000),
            ("system", "Call transferred to +1-800-HUMAN queue.", 14500, 15000),
        ]

    for spk, txt, s_ms, e_ms in transcript_lines:
        db.add(Transcript(
            call_id=call.id,
            speaker=spk,
            text=txt,
            start_timestamp_ms=s_ms,
            end_timestamp_ms=e_ms,
            confidence=0.98
        ))

    # 4. Usage Record
    db.add(UsageRecord(
        organization_id=ctx.organization_id,
        call_id=call.id,
        minutes_used=round(duration / 60.0, 2),
        ai_tokens_used=1250,
        cost_cents=int(call.estimated_cost * 100),
        date=now.strftime("%Y-%m-%d")
    ))

    db.commit()
    db.refresh(call)

    return {
        "status": "success",
        "message": f"Simulated call {call.id} completed successfully.",
        "call_id": call.id,
        "duration_seconds": call.duration_seconds,
        "outcome": call.outcome,
        "summary": call.summary,
    }


@router.post("/outbound")
def place_outbound_call(
    req: OutboundCallRequest,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value, OrgRole.MANAGER.value, OrgRole.OPERATOR.value])),
    db: Session = Depends(get_db),
):
    """
    Manual outbound call.

    Server-side policy gates (hours, suppression, consent, budget, concurrency,
    duplicate-in-progress) are enforced regardless of what the UI sends. High-risk
    calls must be explicitly confirmed.
    """
    if not req.confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This call requires explicit confirmation. Resend with confirmed=true.",
        )

    connection = None
    if req.connection_id:
        connection = (
            db.query(PhoneConnection)
            .filter(
                PhoneConnection.id == req.connection_id,
                PhoneConnection.organization_id == ctx.organization_id,
            )
            .first()
        )
        if not connection:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone connection not found")
    else:
        connection = (
            db.query(PhoneConnection)
            .filter(PhoneConnection.organization_id == ctx.organization_id)
            .order_by(PhoneConnection.created_at.asc())
            .first()
        )

    agent = None
    if req.agent_id:
        agent = (
            db.query(Agent)
            .filter(Agent.id == req.agent_id, Agent.organization_id == ctx.organization_id)
            .first()
        )
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    service = CallSessionService(db, adapter=get_adapter())
    outcome = service.place_outbound(
        ctx.organization,
        connection,
        agent,
        req.to_number,
        initiated_by_user_id=ctx.user.id,
        reason=req.reason,
        metadata=req.metadata,
    )

    db.add(
        AuditLog(
            organization_id=ctx.organization_id,
            user_id=ctx.user.id,
            action="call.outbound_placed",
            entity_type="call",
            entity_id=outcome.call.id if outcome.call else None,
            details={"to_number": req.to_number, "action": outcome.action},
        )
    )
    db.commit()
    return outcome.to_dict()


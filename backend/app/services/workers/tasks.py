"""
Background tasks.

Each task is a plain function taking an explicit ``Session`` so it can run inline
(development / tests) or inside a Celery worker without change. Tasks never
swallow errors: they record failure state on the entity and return a TaskResult.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.call import Call, Transcript
from app.models.campaign import Campaign, CampaignContact
from app.models.contact import Contact
from app.models.knowledge import Document, DocumentChunk, KnowledgeBase
from app.models.telephony import PhoneConnection
from app.models.tenant import Organization
from app.services.calls.session_service import CallSessionService
from app.services.rag import chunk_text, extract_text_from_file, generate_embedding

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    task: str
    ok: bool
    detail: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"task": self.task, "ok": self.ok, "detail": self.detail, "error": self.error}


# --------------------------------------------------------------------------- #
# Document ingestion
# --------------------------------------------------------------------------- #
def ingest_document(
    db: Session,
    document_id: str,
    raw_bytes: bytes,
    *,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> TaskResult:
    """Extract → chunk → embed → persist chunks for a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        return TaskResult("ingest_document", False, error="document_not_found")

    doc.status = "processing"
    db.commit()

    try:
        text = extract_text_from_file(raw_bytes, doc.file_type)
        pieces = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        if not pieces:
            doc.status = "failed"
            doc.error_message = "No extractable text found in the document."
            db.commit()
            return TaskResult("ingest_document", False, error="empty_document")

        # Replace any previous chunks for idempotency.
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete(
            synchronize_session=False
        )

        for idx, content in enumerate(pieces):
            db.add(
                DocumentChunk(
                    organization_id=doc.organization_id,
                    knowledge_base_id=doc.knowledge_base_id,
                    document_id=doc.id,
                    chunk_index=idx,
                    content=content,
                    metadata_json={"chars": len(content)},
                    embedding=generate_embedding(content),
                )
            )

        doc.status = "ready"
        doc.chunk_count = len(pieces)
        doc.error_message = None
        db.commit()
        return TaskResult("ingest_document", True, detail={"chunks": len(pieces)})

    except Exception as exc:  # noqa: BLE001 - record and surface, never crash the worker
        logger.exception("Document ingestion failed for %s", document_id)
        db.rollback()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "failed"
            doc.error_message = f"{type(exc).__name__}: {exc}"
            db.commit()
        return TaskResult("ingest_document", False, error=str(exc))


# --------------------------------------------------------------------------- #
# Call summarisation
# --------------------------------------------------------------------------- #
def _derive_title(turns) -> str:
    for t in turns:
        if t.speaker == "caller" and t.text.strip():
            text = t.text.strip()
            return (text[:57] + "...") if len(text) > 60 else text
    return "Inbound call"


def finalize_call_summary(db: Session, call_id: str) -> TaskResult:
    """Generate a title and summary from the transcript and close the call."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        return TaskResult("finalize_call_summary", False, error="call_not_found")

    turns = (
        db.query(Transcript)
        .filter(Transcript.call_id == call_id)
        .order_by(Transcript.start_timestamp_ms.asc())
        .all()
    )
    if not turns:
        summary = call.summary or "Call completed with no transcript captured."
        title = "Call"
    else:
        caller_lines = [t.text for t in turns if t.speaker == "caller"]
        agent_lines = [t.text for t in turns if t.speaker == "agent"]
        title = _derive_title(turns)
        parts = []
        if caller_lines:
            parts.append(f"Caller intent: {caller_lines[0].strip()}")
        if agent_lines:
            parts.append(f"Agent handled with {len(agent_lines)} responses.")
        if len(caller_lines) > 1:
            parts.append(f"Final caller remark: {caller_lines[-1].strip()}")
        summary = " ".join(parts) or "Conversation captured."

    call.summary = summary
    service = CallSessionService(db)
    service.finalize(call, summary=summary)

    return TaskResult(
        "finalize_call_summary",
        True,
        detail={"call_id": call_id, "title": title, "summary": summary, "turns": len(turns)},
    )


# --------------------------------------------------------------------------- #
# Campaign dialing
# --------------------------------------------------------------------------- #
def campaign_dialer_sweep(db: Session, campaign_id: str, max_calls: int = 5) -> TaskResult:
    """Place outbound calls for eligible pending campaign contacts."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return TaskResult("campaign_dialer_sweep", False, error="campaign_not_found")

    if campaign.status in ("cancelled", "completed"):
        return TaskResult("campaign_dialer_sweep", True, detail={"dialed": 0, "reason": "inactive"})

    organization = db.query(Organization).filter(Organization.id == campaign.organization_id).first()
    agent = db.query(Agent).filter(Agent.id == campaign.agent_id).first()
    connection = None
    if campaign.caller_connection_id:
        connection = (
            db.query(PhoneConnection).filter(PhoneConnection.id == campaign.caller_connection_id).first()
        )

    pending = (
        db.query(CampaignContact)
        .filter(
            CampaignContact.campaign_id == campaign.id,
            CampaignContact.status == "pending",
            CampaignContact.attempts_count < campaign.max_attempts,
        )
        .limit(max_calls)
        .all()
    )

    dialed, blocked, failed = 0, 0, 0
    service = CallSessionService(db)
    for cc in pending:
        contact = db.query(Contact).filter(Contact.id == cc.contact_id).first()
        if not contact:
            cc.status = "failed"
            failed += 1
            continue

        outcome = service.place_outbound(
            organization,
            connection,
            agent,
            contact.phone_number,
            campaign_id=campaign.id,
            contact_id=contact.id,
            reason=f"campaign:{campaign.name}",
        )
        cc.attempts_count += 1
        cc.last_attempt_at = datetime.now(timezone.utc)
        cc.call_id = outcome.call.id if outcome.call else None
        if outcome.action == "initiated":
            cc.status = "calling"
            dialed += 1
        elif outcome.action == "blocked":
            cc.status = "opted_out"
            blocked += 1
        else:
            cc.status = "failed"
            failed += 1
        db.commit()

    campaign.total_contacts = len(campaign.contacts) or campaign.total_contacts
    # Only genuinely failed attempts count as failures. Contacts the policy
    # refused (DNC, no consent, unverified line, outside hours) are recorded as
    # opted_out and reported separately rather than inflating the failure count.
    campaign.failed_calls = (campaign.failed_calls or 0) + failed
    db.commit()
    return TaskResult(
        "campaign_dialer_sweep",
        True,
        detail={"dialed": dialed, "blocked": blocked, "failed": failed, "campaign_id": campaign.id},
    )

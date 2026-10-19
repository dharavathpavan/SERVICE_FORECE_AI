from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_role, TenantContext
from app.models.tenant import OrgRole, AuditLog, Organization
from app.models.campaign import Campaign, CampaignContact
from app.models.contact import Contact, SuppressionEntry
from app.models.agent import Agent
from app.models.telephony import PhoneConnection
from app.services.calls.policy import PolicyEngine, within_calling_hours
from app.services.workers.tasks import campaign_dialer_sweep

router = APIRouter(prefix="/campaigns", tags=["Outbound Campaigns"])


class CampaignCreate(BaseModel):
    name: str
    agent_id: str
    caller_connection_id: Optional[str] = None
    allowed_start_hour: str = "09:00"
    allowed_end_hour: str = "20:00"
    timezone: str = "UTC"
    max_attempts: int = Field(3, ge=1, le=5)
    retry_delay_minutes: int = Field(60, ge=15, le=1440)
    concurrency_limit: int = Field(2, ge=1, le=10)
    contact_ids: List[str] = []


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    allowed_start_hour: Optional[str] = None
    allowed_end_hour: Optional[str] = None
    max_attempts: Optional[int] = None
    concurrency_limit: Optional[int] = None


@router.get("")
def list_campaigns(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Lists outbound calling campaigns for the tenant."""
    campaigns = db.query(Campaign).filter(Campaign.organization_id == ctx.organization_id).all()
    return campaigns


@router.post("", status_code=status.HTTP_201_CREATED)
def create_campaign(
    c_in: CampaignCreate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Creates a new outbound campaign in Draft status. Never auto-starts calls upon creation."""
    # Verify Agent
    agent = db.query(Agent).filter(
        Agent.id == c_in.agent_id,
        Agent.organization_id == ctx.organization_id
    ).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned agent not found")

    campaign = Campaign(
        organization_id=ctx.organization_id,
        name=c_in.name,
        agent_id=c_in.agent_id,
        caller_connection_id=c_in.caller_connection_id,
        status="draft",
        allowed_start_hour=c_in.allowed_start_hour,
        allowed_end_hour=c_in.allowed_end_hour,
        timezone=c_in.timezone,
        max_attempts=c_in.max_attempts,
        retry_delay_minutes=c_in.retry_delay_minutes,
        concurrency_limit=c_in.concurrency_limit,
        total_contacts=len(c_in.contact_ids),
        successful_calls=0,
        failed_calls=0,
    )
    db.add(campaign)
    db.flush()

    # Attach contacts (filtering out any that are on the suppression list)
    added = 0
    for cid in c_in.contact_ids:
        contact = db.query(Contact).filter(
            Contact.id == cid,
            Contact.organization_id == ctx.organization_id,
            Contact.is_suppressed == False
        ).first()
        if contact:
            db.add(CampaignContact(campaign_id=campaign.id, contact_id=contact.id, status="pending"))
            added += 1

    campaign.total_contacts = added
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}")
def get_campaign(
    campaign_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Retrieves campaign metrics and configuration."""
    camp = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.organization_id == ctx.organization_id
    ).first()
    if not camp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return camp


@router.post("/{campaign_id}/dry-run")
def preview_campaign_dry_run(
    campaign_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Previews a run without dialling anything:

    - evaluates the calling window in the campaign's own timezone
    - puts every pending contact through the same policy engine the dialer uses,
      so refused numbers are listed with the exact reason
    """
    camp = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.organization_id == ctx.organization_id
    ).first()
    if not camp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    organization = db.query(Organization).filter(Organization.id == ctx.organization_id).first()
    agent = db.query(Agent).filter(
        Agent.id == camp.agent_id,
        Agent.organization_id == ctx.organization_id
    ).first()
    connection = None
    if camp.caller_connection_id:
        connection = db.query(PhoneConnection).filter(
            PhoneConnection.id == camp.caller_connection_id,
            PhoneConnection.organization_id == ctx.organization_id
        ).first()

    now = datetime.now(timezone.utc)
    is_within_calling_window = within_calling_hours(
        camp.allowed_start_hour, camp.allowed_end_hour, now, camp.timezone
    )

    pending = db.query(CampaignContact).filter(
        CampaignContact.campaign_id == camp.id,
        CampaignContact.status == "pending",
        CampaignContact.attempts_count < camp.max_attempts
    ).all()

    policy = PolicyEngine(db)
    would_dial = 0
    blocked: List[dict] = []
    for cc in pending:
        contact = db.query(Contact).filter(Contact.id == cc.contact_id).first()
        if not contact:
            continue
        decision = policy.evaluate_outbound(
            organization,
            connection,
            agent,
            contact.phone_number,
            now=now,
            tz_name=camp.timezone,
            start_hour=camp.allowed_start_hour,
            end_hour=camp.allowed_end_hour,
            concurrency_limit=camp.concurrency_limit,
        )
        if decision.allowed:
            would_dial += 1
        else:
            blocked.append({
                "contact_id": contact.id,
                "phone_number": contact.phone_number,
                "reasons": decision.codes,
                "violations": [v.to_dict() for v in decision.violations],
            })

    warnings: List[str] = []
    if not is_within_calling_window:
        warnings.append(
            f"Now is outside the allowed window "
            f"({camp.allowed_start_hour}-{camp.allowed_end_hour} {camp.timezone})."
        )
    if connection is None:
        warnings.append("No calling line is attached to this campaign.")
    elif not connection.is_verified:
        warnings.append(f"Calling line {connection.phone_number} is not verified yet.")
    if agent is None:
        warnings.append("The assigned agent no longer exists.")
    if not pending:
        warnings.append("There are no pending contacts left to dial.")

    return {
        "campaign_id": camp.id,
        "campaign_name": camp.name,
        "status": camp.status,
        "total_contacts": db.query(CampaignContact).filter(CampaignContact.campaign_id == camp.id).count(),
        "pending_contacts": len(pending),
        "would_dial": would_dial,
        "would_block": len(blocked),
        "blocked": blocked[:25],
        "is_within_calling_window": is_within_calling_window,
        "calling_window": f"{camp.allowed_start_hour} to {camp.allowed_end_hour} ({camp.timezone})",
        "current_time": now.isoformat(),
        "concurrency_limit": camp.concurrency_limit,
        "max_attempts": camp.max_attempts,
        "can_activate": len(pending) > 0 and is_within_calling_window,
        "validation_warnings": warnings,
    }


def _run_sweep(db: Session, campaign: Campaign) -> dict:
    """Run one dialer pass and report honestly what it did."""
    result = campaign_dialer_sweep(db, campaign.id, max_calls=campaign.concurrency_limit)
    detail = result.detail or {}
    return {
        "dialed": detail.get("dialed", 0),
        "blocked": detail.get("blocked", 0),
        "failed": detail.get("failed", 0),
        "error": result.error,
    }


@router.post("/{campaign_id}/start")
def start_campaign(
    campaign_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """
    Explicitly activates the campaign and runs one dialer pass.

    Nothing is dialled until this is called. The pass places at most
    ``concurrency_limit`` calls and every contact still goes through the policy
    engine, so refusals are recorded rather than silently dropped.
    """
    camp = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.organization_id == ctx.organization_id
    ).first()
    if not camp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    camp.status = "running"
    audit = AuditLog(
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        action="campaign.started",
        entity_type="campaign",
        entity_id=camp.id,
        details={"name": camp.name, "total_contacts": camp.total_contacts}
    )
    db.add(audit)
    db.commit()
    db.refresh(camp)

    sweep = _run_sweep(db, camp)
    db.refresh(camp)
    return {
        "status": "running",
        "message": f"Campaign '{camp.name}' is now active.",
        **sweep,
    }


@router.post("/{campaign_id}/sweep")
def sweep_campaign(
    campaign_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """
    Runs one more dialer pass. Safe to call repeatedly: contacts already dialled
    are skipped, and each pass places at most ``concurrency_limit`` calls.
    """
    camp = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.organization_id == ctx.organization_id
    ).first()
    if not camp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    if camp.status != "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Campaign must be running to dial (it is '{camp.status}').",
        )

    sweep = _run_sweep(db, camp)
    db.refresh(camp)
    return {"status": camp.status, **sweep}


@router.post("/{campaign_id}/pause")
def pause_campaign(
    campaign_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Pauses outbound calling."""
    camp = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.organization_id == ctx.organization_id
    ).first()
    if not camp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    camp.status = "paused"
    db.commit()
    return {"status": "paused", "message": f"Campaign '{camp.name}' has been paused."}

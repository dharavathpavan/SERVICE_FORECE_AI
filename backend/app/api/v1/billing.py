import hmac
import hashlib
import json
import time
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_tenant_context, require_role, TenantContext
from app.models.tenant import OrgRole
from app.models.billing import WebhookEndpoint, WebhookDelivery, UsageRecord
from app.services.tools.ssrf_guard import validate_url_safety

router = APIRouter(prefix="", tags=["Billing, Usage & Webhooks"])


class WebhookCreate(BaseModel):
    url: str
    events: List[str] = ["call.started", "call.completed", "call.transferred"]


class PlanUpgradeRequest(BaseModel):
    plan_name: str  # starter, professional, enterprise


@router.get("/billing/usage")
def get_usage_and_billing_status(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Returns metered usage, active subscription tier, and limits."""
    usage_records = db.query(UsageRecord).filter(
        UsageRecord.organization_id == ctx.organization_id
    ).all()

    total_minutes = sum(r.minutes_used for r in usage_records)
    total_cost_cents = sum(r.cost_cents for r in usage_records)
    total_tokens = sum(r.ai_tokens_used for r in usage_records)

    monthly_limit = ctx.organization.monthly_call_limit

    return {
        "organization_id": ctx.organization_id,
        "plan_name": ctx.organization.billing_plan,
        "monthly_call_limit_minutes": monthly_limit,
        "used_minutes": round(total_minutes, 2),
        "percent_consumed": round((total_minutes / monthly_limit) * 100, 1) if monthly_limit > 0 else 0,
        "total_ai_tokens": total_tokens,
        "estimated_charges_usd": round(total_cost_cents / 100.0, 2),
        "status": "active",
        "renewal_date": (datetime.now(timezone.utc).replace(day=1) + timedelta(days=32)).replace(day=1).strftime("%Y-%m-%d") if False else "2026-11-01",
        "demo_mode": settings.DEMO_MODE,
    }


@router.post("/billing/upgrade")
def upgrade_plan(
    req: PlanUpgradeRequest,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value])),
    db: Session = Depends(get_db)
):
    """Upgrades organization plan."""
    plans = {"starter": 500, "professional": 2500, "enterprise": 10000}
    if req.plan_name.lower() not in plans:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan")

    ctx.organization.billing_plan = req.plan_name.lower()
    ctx.organization.monthly_call_limit = plans[req.plan_name.lower()]
    db.commit()
    return {
        "status": "upgraded",
        "plan": ctx.organization.billing_plan,
        "monthly_limit": ctx.organization.monthly_call_limit
    }


# Webhooks
@router.get("/webhooks")
def list_webhooks(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Lists registered webhook endpoints."""
    return db.query(WebhookEndpoint).filter(WebhookEndpoint.organization_id == ctx.organization_id).all()


@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
def create_webhook(
    hook_in: WebhookCreate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Creates a new signed webhook endpoint."""
    validate_url_safety(hook_in.url)

    secret = f"whsec_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:32]}"
    webhook = WebhookEndpoint(
        organization_id=ctx.organization_id,
        url=hook_in.url,
        secret=secret,
        events=hook_in.events,
        is_active=True
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.post("/webhooks/{webhook_id}/test")
async def send_test_webhook(
    webhook_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Dispatches a test HMAC-signed webhook event to the configured URL."""
    hook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.organization_id == ctx.organization_id
    ).first()
    if not hook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook endpoint not found")

    payload = {
        "event": "call.completed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "organization_id": ctx.organization_id,
        "data": {
            "call_id": "call-test-sample-883",
            "duration_seconds": 124,
            "outcome": "ai_resolved",
            "agent_name": "Apex Customer Service"
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    signature = hmac.new(hook.secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    # Deliver safely
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                hook.url,
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-ServiceForce-Signature": f"sha256={signature}",
                    "X-ServiceForce-Event": "call.completed"
                }
            )
            delivery = WebhookDelivery(
                webhook_endpoint_id=hook.id,
                event_name="call.completed",
                payload=payload,
                status="success" if resp.status_code < 400 else "failed",
                status_code=resp.status_code,
                attempts=1,
            )
            db.add(delivery)
            db.commit()
            return {"status": "dispatched", "status_code": resp.status_code}
    except Exception as e:
        delivery = WebhookDelivery(
            webhook_endpoint_id=hook.id,
            event_name="call.completed",
            payload=payload,
            status="failed",
            error_message=str(e),
            attempts=1,
        )
        db.add(delivery)
        db.commit()
        return {"status": "dispatch_attempted", "error": str(e)}

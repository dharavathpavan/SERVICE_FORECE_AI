from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_tenant_context, TenantContext
from app.models.call import Call, CallEvent
from app.models.agent import Agent
from app.models.billing import UsageRecord
from app.models.campaign import Campaign

router = APIRouter(prefix="/analytics", tags=["Analytics & Reporting"])


@router.get("/summary")
def get_analytics_summary(
    days: int = 30,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Computes real aggregated metrics for the organization.
    Distinguishes measured values from estimates.
    """
    now = datetime.now(timezone.utc)
    since_date = now - timedelta(days=days)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    # 1. Calls total & today
    total_calls = db.query(Call).filter(
        Call.organization_id == ctx.organization_id,
        Call.created_at >= since_date
    ).count()

    calls_today = db.query(Call).filter(
        Call.organization_id == ctx.organization_id,
        Call.created_at >= today_start
    ).count()

    # 2. Outcomes
    answered_calls = db.query(Call).filter(
        Call.organization_id == ctx.organization_id,
        Call.created_at >= since_date,
        Call.status.in_(["completed", "transferred", "in_progress"])
    ).count()

    failed_calls = db.query(Call).filter(
        Call.organization_id == ctx.organization_id,
        Call.created_at >= since_date,
        Call.status.in_(["failed", "no_answer", "busy"])
    ).count()

    ai_resolved_calls = db.query(Call).filter(
        Call.organization_id == ctx.organization_id,
        Call.created_at >= since_date,
        # Only a call that actually ran to completion can count as resolved:
        # calls still in flight, or never finalised, have no outcome recorded.
        Call.status.in_(["completed", "transferred"]),
        Call.outcome == "ai_resolved"
    ).count()

    human_transfers = db.query(Call).filter(
        Call.organization_id == ctx.organization_id,
        Call.created_at >= since_date,
        Call.outcome == "human_transferred"
    ).count()

    # 3. Durations and Minutes
    durations = db.query(func.sum(Call.duration_seconds), func.avg(Call.duration_seconds)).filter(
        Call.organization_id == ctx.organization_id,
        Call.created_at >= since_date
    ).first()

    total_duration_sec = durations[0] or 0
    avg_duration_sec = round(durations[1] or 0, 1)
    total_minutes = round(total_duration_sec / 60.0, 2)

    # 4. Usage costs
    total_cost = db.query(func.sum(Call.estimated_cost)).filter(
        Call.organization_id == ctx.organization_id,
        Call.created_at >= since_date
    ).scalar() or 0.0

    # 5. Active agents & campaigns
    active_agents = db.query(Agent).filter(
        Agent.organization_id == ctx.organization_id,
        Agent.is_active == True
    ).count()

    running_campaigns = db.query(Campaign).filter(
        Campaign.organization_id == ctx.organization_id,
        Campaign.status == "running"
    ).count()

    # 6. Rates
    answer_rate = round((answered_calls / total_calls * 100), 1) if total_calls > 0 else 0.0
    resolution_rate = round((ai_resolved_calls / answered_calls * 100), 1) if answered_calls > 0 else 0.0
    transfer_rate = round((human_transfers / answered_calls * 100), 1) if answered_calls > 0 else 0.0

    # 7. Time series (last 7 days)
    daily_volume = []
    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        day_str = day_date.strftime("%Y-%m-%d")
        day_label = day_date.strftime("%b %d")
        day_start = datetime(day_date.year, day_date.month, day_date.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)

        count = db.query(Call).filter(
            Call.organization_id == ctx.organization_id,
            Call.created_at >= day_start,
            Call.created_at < day_end
        ).count()

        resolved = db.query(Call).filter(
            Call.organization_id == ctx.organization_id,
            Call.created_at >= day_start,
            Call.created_at < day_end,
            Call.outcome == "ai_resolved"
        ).count()

        transferred = db.query(Call).filter(
            Call.organization_id == ctx.organization_id,
            Call.created_at >= day_start,
            Call.created_at < day_end,
            Call.outcome == "human_transferred"
        ).count()

        daily_volume.append({
            "date": day_str,
            "label": day_label,
            "total_calls": count,
            "ai_resolved": resolved,
            "transferred": transferred
        })

    return {
        "calls_today": calls_today,
        "total_calls": total_calls,
        "answered_calls": answered_calls,
        "failed_calls": failed_calls,
        "ai_resolved_calls": ai_resolved_calls,
        "human_transfers": human_transfers,
        "total_minutes": total_minutes,
        "avg_duration_seconds": avg_duration_sec,
        "estimated_usage_cost_usd": round(total_cost, 2),
        "active_agents": active_agents,
        "running_campaigns": running_campaigns,
        "answer_rate_pct": answer_rate,
        "ai_resolution_rate_pct": resolution_rate,
        "human_transfer_rate_pct": transfer_rate,
        "daily_volume": daily_volume,
        "currency": "USD"
    }

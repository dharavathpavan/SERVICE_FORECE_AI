from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_role, TenantContext
from app.models.tenant import OrgRole, AuditLog

router = APIRouter(prefix="/audit-logs", tags=["Audit Trail"])


@router.get("")
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Lists tamper-evident tenant audit logs."""
    q = db.query(AuditLog).filter(AuditLog.organization_id == ctx.organization_id)
    if action:
        q = q.filter(AuditLog.action.like(f"%{action}%"))

    total = q.count()
    logs = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": l.id,
                "user_id": l.user_id,
                "action": l.action,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
                "details": l.details or {},
                "created_at": l.created_at,
            }
            for l in logs
        ]
    }

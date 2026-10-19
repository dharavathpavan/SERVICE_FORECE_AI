from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_role, TenantContext
from app.models.tenant import OrgRole, AuditLog
from app.models.telephony import PhoneConnection, Gateway
from app.services.telephony.factory import get_adapter, UnknownTelephonyProvider
from app.services.telephony.gateway_service import (
    STATUS_UNVERIFIED,
    summarize_gateway,
    verify_gateway,
    verify_phone_connection,
)
from app.services.telephony.types import TelephonyError

router = APIRouter(prefix="", tags=["Telephony & Gateways"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class PhoneConnectionCreate(BaseModel):
    friendly_name: str
    phone_number: str
    connection_type: str = "mock"  # mock, gsm_gateway, sip_trunk
    inbound_enabled: bool = True
    outbound_enabled: bool = True
    assigned_agent_id: Optional[str] = None
    gateway_id: Optional[str] = None


class PhoneConnectionUpdate(BaseModel):
    friendly_name: Optional[str] = None
    inbound_enabled: Optional[bool] = None
    outbound_enabled: Optional[bool] = None
    assigned_agent_id: Optional[str] = None


class GatewayCreate(BaseModel):
    identifier: str = Field(..., min_length=2, max_length=100)
    sip_endpoint: str = Field(..., min_length=3, max_length=255)


def _serialize_connection(conn: PhoneConnection) -> Dict[str, Any]:
    return {
        "id": conn.id,
        "friendly_name": conn.friendly_name,
        "phone_number": conn.phone_number,
        "connection_type": conn.connection_type,
        "is_verified": conn.is_verified,
        "health_status": conn.health_status,
        "last_health_check": conn.last_health_check,
        "inbound_enabled": conn.inbound_enabled,
        "outbound_enabled": conn.outbound_enabled,
        "assigned_agent_id": conn.assigned_agent_id,
        "provider_config": conn.provider_config or {},
        "created_at": conn.created_at,
    }


# --------------------------------------------------------------------------- #
# Adapter introspection
# --------------------------------------------------------------------------- #
@router.get("/telephony/capabilities")
def get_telephony_capabilities(
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Report exactly what the configured telephony provider can and cannot do."""
    try:
        adapter = get_adapter()
    except UnknownTelephonyProvider as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return adapter.capabilities().to_dict()


@router.get("/telephony/health")
def get_telephony_health(
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Non-throwing provider health, including a live connectivity probe."""
    try:
        adapter = get_adapter()
    except UnknownTelephonyProvider as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return adapter.health()


# --------------------------------------------------------------------------- #
# Phone connections
# --------------------------------------------------------------------------- #
@router.get("/phone-connections")
def list_phone_connections(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """Lists all configured phone connections for the tenant."""
    rows = (
        db.query(PhoneConnection)
        .filter(PhoneConnection.organization_id == ctx.organization_id)
        .all()
    )
    return [_serialize_connection(c) for c in rows]


@router.post("/phone-connections", status_code=status.HTTP_201_CREATED)
def create_phone_connection(
    conn_in: PhoneConnectionCreate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db),
):
    """
    Registers a business phone connection or BYO SIM gateway number.

    The number starts **unverified**. It only becomes verified after a real probe
    via ``POST /phone-connections/{id}/verify`` succeeds against the gateway.
    """
    conn = PhoneConnection(
        organization_id=ctx.organization_id,
        friendly_name=conn_in.friendly_name,
        phone_number=conn_in.phone_number,
        connection_type=conn_in.connection_type,
        is_verified=False,
        health_status="unverified",
        last_health_check=None,
        inbound_enabled=conn_in.inbound_enabled,
        outbound_enabled=conn_in.outbound_enabled,
        assigned_agent_id=conn_in.assigned_agent_id,
        provider_config={"gateway_id": conn_in.gateway_id} if conn_in.gateway_id else {},
    )
    db.add(conn)
    db.flush()

    db.add(
        AuditLog(
            organization_id=ctx.organization_id,
            user_id=ctx.user.id,
            action="phone_connection.created",
            entity_type="phone_connection",
            entity_id=conn.id,
            details={"phone_number": conn.phone_number, "type": conn.connection_type},
        )
    )
    db.commit()
    db.refresh(conn)
    return _serialize_connection(conn)


@router.patch("/phone-connections/{connection_id}")
def update_phone_connection(
    connection_id: str,
    conn_in: PhoneConnectionUpdate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db),
):
    """Updates routing settings for a phone number."""
    conn = (
        db.query(PhoneConnection)
        .filter(
            PhoneConnection.id == connection_id,
            PhoneConnection.organization_id == ctx.organization_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone connection not found")

    for field, val in conn_in.model_dump(exclude_unset=True).items():
        setattr(conn, field, val)

    db.commit()
    db.refresh(conn)
    return _serialize_connection(conn)


@router.post("/phone-connections/{connection_id}/verify")
def verify_phone_connection_endpoint(
    connection_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db),
):
    """Actively probe the SIM/line and update verification state. Never fakes success."""
    conn = (
        db.query(PhoneConnection)
        .filter(
            PhoneConnection.id == connection_id,
            PhoneConnection.organization_id == ctx.organization_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone connection not found")

    result = verify_phone_connection(db, conn)
    if not result.ok and not conn.is_verified:
        # 200 with an honest negative result: this is a verification outcome, not a crash.
        return {
            "verified": False,
            "status": conn.health_status,
            "message": result.message,
            "lines": [ln.to_dict() for ln in result.lines],
        }

    return {
        "verified": conn.is_verified,
        "status": conn.health_status,
        "message": result.message,
        "line": next(
            (ln.to_dict() for ln in result.lines if ln.phone_number == conn.phone_number),
            None,
        ),
    }


@router.delete("/phone-connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_phone_connection(
    connection_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db),
):
    """Deletes a phone connection."""
    conn = (
        db.query(PhoneConnection)
        .filter(
            PhoneConnection.id == connection_id,
            PhoneConnection.organization_id == ctx.organization_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone connection not found")

    db.delete(conn)
    db.commit()
    return None


# --------------------------------------------------------------------------- #
# Gateways
# --------------------------------------------------------------------------- #
@router.get("/gateways")
def list_gateways(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """Lists registered SIP / GSM hardware gateways with derived health."""
    rows = db.query(Gateway).filter(Gateway.organization_id == ctx.organization_id).all()
    return [summarize_gateway(g) for g in rows]


@router.post("/gateways", status_code=status.HTTP_201_CREATED)
def register_gateway(
    gw_in: GatewayCreate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db),
):
    """
    Registers a SIP trunk endpoint or GSM/VoLTE gateway.

    The gateway starts ``unverified``. It is only marked online after
    ``POST /gateways/{id}/verify`` performs a real connectivity probe.
    """
    existing = (
        db.query(Gateway)
        .filter(
            Gateway.organization_id == ctx.organization_id,
            Gateway.identifier == gw_in.identifier,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have a gateway with identifier '{gw_in.identifier}'.",
        )

    gw = Gateway(
        organization_id=ctx.organization_id,
        identifier=gw_in.identifier,
        sip_endpoint=gw_in.sip_endpoint,
        status=STATUS_UNVERIFIED,
        last_heartbeat=None,
        health_details={"message": "Not yet verified."},
    )
    db.add(gw)
    db.flush()
    db.add(
        AuditLog(
            organization_id=ctx.organization_id,
            user_id=ctx.user.id,
            action="gateway.registered",
            entity_type="gateway",
            entity_id=gw.id,
            details={"identifier": gw.identifier, "sip_endpoint": gw.sip_endpoint},
        )
    )
    db.commit()
    db.refresh(gw)
    return summarize_gateway(gw)


@router.post("/gateways/{gateway_id}/verify")
def verify_gateway_endpoint(
    gateway_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db),
):
    """Runs a real connectivity + line probe and persists the outcome."""
    gw = (
        db.query(Gateway)
        .filter(Gateway.id == gateway_id, Gateway.organization_id == ctx.organization_id)
        .first()
    )
    if not gw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway not found")

    result = verify_gateway(db, gw)
    return {**summarize_gateway(gw), "probe": result.to_dict()}


@router.get("/gateways/{gateway_id}/lines")
def get_gateway_lines(
    gateway_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """Returns live SIM/line status for a gateway."""
    gw = (
        db.query(Gateway)
        .filter(Gateway.id == gateway_id, Gateway.organization_id == ctx.organization_id)
        .first()
    )
    if not gw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway not found")

    try:
        adapter = get_adapter()
        lines = adapter.get_line_status()
        return {"gateway_id": gw.id, "lines": [ln.to_dict() for ln in lines]}
    except TelephonyError as exc:
        # Honest failure: return the error rather than an empty success.
        return {"gateway_id": gw.id, "lines": [], "error": exc.to_dict()}


@router.delete("/gateways/{gateway_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gateway(
    gateway_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db),
):
    gw = (
        db.query(Gateway)
        .filter(Gateway.id == gateway_id, Gateway.organization_id == ctx.organization_id)
        .first()
    )
    if not gw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway not found")
    db.delete(gw)
    db.commit()
    return None


@router.post("/gateways/{gateway_id}/heartbeat")
def gateway_heartbeat(
    gateway_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """Records a heartbeat pushed by the on-premise gateway bridge."""
    gw = (
        db.query(Gateway)
        .filter(Gateway.id == gateway_id, Gateway.organization_id == ctx.organization_id)
        .first()
    )
    if not gw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway not found")

    gw.status = "online"
    gw.last_heartbeat = datetime.now(timezone.utc)
    gw.health_details = {**(gw.health_details or {}), "registration": "OK", "source": "heartbeat"}
    db.commit()
    return {"status": "heartbeat_acknowledged", "gateway_status": gw.status}

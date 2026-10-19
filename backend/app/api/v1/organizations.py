import secrets
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_role, TenantContext
from app.models.tenant import Organization, OrganizationMembership, Invitation, User, AuditLog, OrgRole
from app.schemas.organization import (
    OrganizationResponse,
    MembershipResponse,
    InvitationCreate,
    InvitationResponse,
    RoleUpdate,
)
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/organizations", tags=["Organizations & Team"])


@router.get("/current", response_model=OrganizationResponse)
def get_current_organization(ctx: TenantContext = Depends(get_tenant_context)):
    """Returns details of the active tenant organization."""
    return ctx.organization


@router.get("/members", response_model=List[MembershipResponse])
def list_organization_members(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Lists all members of the active organization."""
    memberships = db.query(OrganizationMembership).filter(
        OrganizationMembership.organization_id == ctx.organization_id
    ).all()
    
    results = []
    for m in memberships:
        user_res = UserResponse.model_validate(m.user) if m.user else None
        results.append(MembershipResponse(
            id=m.id,
            organization_id=m.organization_id,
            user_id=m.user_id,
            role=m.role,
            created_at=m.created_at,
            user=user_res
        ))
    return results


@router.post("/invite", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
def invite_team_member(
    inv_in: InvitationCreate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Sends an invitation to a new team member. Restricted to Owner and Admin."""
    existing_inv = db.query(Invitation).filter(
        Invitation.organization_id == ctx.organization_id,
        Invitation.email == inv_in.email,
        Invitation.status == "pending"
    ).first()

    if existing_inv:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pending invitation already exists for this email")

    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        organization_id=ctx.organization_id,
        email=inv_in.email,
        role=inv_in.role,
        token=token,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(invitation)

    audit = AuditLog(
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        action="team.invited",
        entity_type="invitation",
        entity_id=invitation.id,
        details={"invited_email": inv_in.email, "role": inv_in.role}
    )
    db.add(audit)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.get("/invitations", response_model=List[InvitationResponse])
def list_invitations(
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Lists pending invitations for the organization."""
    return db.query(Invitation).filter(
        Invitation.organization_id == ctx.organization_id
    ).all()


@router.patch("/members/{membership_id}", response_model=MembershipResponse)
def update_member_role(
    membership_id: str,
    role_in: RoleUpdate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value])),
    db: Session = Depends(get_db)
):
    """Update a team member's role. Restricted to Owner."""
    membership = db.query(OrganizationMembership).filter(
        OrganizationMembership.id == membership_id,
        OrganizationMembership.organization_id == ctx.organization_id
    ).first()

    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    if membership.user_id == ctx.user.id and role_in.role != OrgRole.OWNER.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot downgrade own Owner role")

    membership.role = role_in.role
    db.commit()
    db.refresh(membership)
    return membership


@router.delete("/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    membership_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Remove a team member from the organization."""
    membership = db.query(OrganizationMembership).filter(
        OrganizationMembership.id == membership_id,
        OrganizationMembership.organization_id == ctx.organization_id
    ).first()

    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    if membership.user_id == ctx.user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove yourself from organization")

    if membership.role == OrgRole.OWNER.value and ctx.role != OrgRole.OWNER.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Owners can remove another Owner")

    db.delete(membership)
    db.commit()
    return None

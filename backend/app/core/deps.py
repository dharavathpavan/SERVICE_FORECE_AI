from typing import Generator, Optional, List
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.tenant import User, Organization, OrganizationMembership, OrgRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)


class TenantContext:
    def __init__(self, organization: Organization, user: User, role: str):
        self.organization = organization
        self.user = user
        self.role = role
        self.organization_id = organization.id


def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def get_tenant_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id")
) -> TenantContext:
    """Enforces multi-tenancy: verifies user's organization membership and attaches organization and role."""
    # Find all memberships for current user
    memberships = db.query(OrganizationMembership).filter(
        OrganizationMembership.user_id == current_user.id
    ).all()

    if not memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User belongs to no active organization")

    target_membership = None
    if x_organization_id:
        target_membership = next((m for m in memberships if m.organization_id == x_organization_id), None)
        if not target_membership:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to requested organization")
    else:
        # Default to first organization membership
        target_membership = memberships[0]

    org = db.query(Organization).filter(
        Organization.id == target_membership.organization_id,
        Organization.is_active == True
    ).first()

    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found or inactive")

    return TenantContext(organization=org, user=current_user, role=target_membership.role)


def require_role(allowed_roles: List[str]):
    """Role-based access control (RBAC) dependency factory."""
    def role_checker(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        # Owner has access to everything
        if ctx.role == OrgRole.OWNER.value:
            return ctx
        if ctx.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {', '.join(allowed_roles)}. Current role: {ctx.role}"
            )
        return ctx
    return role_checker

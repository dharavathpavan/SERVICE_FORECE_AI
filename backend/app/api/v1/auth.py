import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.deps import get_current_user, get_tenant_context, TenantContext
from app.models.tenant import User, Organization, OrganizationMembership, OrgRole, AuditLog
from app.schemas.auth import UserCreate, UserLogin, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-") or "org"


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user, creates their primary organization, and sets their role as Owner."""
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create User
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Create default Organization
    org_name = user_in.organization_name or f"{user_in.full_name}'s Org"
    base_slug = slugify(org_name)
    slug = base_slug
    counter = 1
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(
        name=org_name,
        slug=slug,
        is_active=True,
        billing_plan="starter",
        monthly_call_limit=500
    )
    db.add(org)
    db.flush()

    # Create Owner Membership
    membership = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role=OrgRole.OWNER.value,
    )
    db.add(membership)

    # Audit log
    audit = AuditLog(
        organization_id=org.id,
        user_id=user.id,
        action="tenant.registered",
        entity_type="organization",
        entity_id=org.id,
        details={"user_email": user.email, "org_name": org.name}
    )
    db.add(audit)
    db.commit()
    db.refresh(user)
    db.refresh(org)

    token = create_access_token(subject=user.id, organization_id=org.id, role=OrgRole.OWNER.value)
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        organization_id=org.id,
        organization_name=org.name,
        role=OrgRole.OWNER.value,
    )


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """Authenticates email and password, returning JWT access token with tenant context."""
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is deactivated")

    # Fetch memberships
    memberships = db.query(OrganizationMembership).filter(
        OrganizationMembership.user_id == user.id
    ).all()

    if not memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active organization found for user")

    primary_membership = memberships[0]
    org = db.query(Organization).filter(Organization.id == primary_membership.organization_id).first()

    token = create_access_token(
        subject=user.id,
        organization_id=primary_membership.organization_id,
        role=primary_membership.role
    )

    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        organization_id=org.id if org else primary_membership.organization_id,
        organization_name=org.name if org else "Default",
        role=primary_membership.role,
    )


@router.get("/me")
def get_current_user_profile(
    ctx: TenantContext = Depends(get_tenant_context)
):
    """Returns current authenticated user details and active organization context."""
    return {
        "user": UserResponse.model_validate(ctx.user),
        "organization": {
            "id": ctx.organization.id,
            "name": ctx.organization.name,
            "slug": ctx.organization.slug,
            "billing_plan": ctx.organization.billing_plan,
            "monthly_call_limit": ctx.organization.monthly_call_limit,
        },
        "role": ctx.role,
    }

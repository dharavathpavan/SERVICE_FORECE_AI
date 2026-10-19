from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from app.schemas.auth import UserResponse


class OrganizationBase(BaseModel):
    name: str


class OrganizationCreate(OrganizationBase):
    slug: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    id: str
    slug: str
    is_active: bool
    billing_plan: str
    monthly_call_limit: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MembershipResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    role: str
    created_at: datetime
    user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "operator"


class InvitationResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    role: str
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    role: str

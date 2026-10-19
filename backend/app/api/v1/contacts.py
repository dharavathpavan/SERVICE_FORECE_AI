import csv
import io
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_role, TenantContext
from app.models.tenant import OrgRole, AuditLog
from app.models.contact import Contact, ConsentRecord, SuppressionEntry

router = APIRouter(prefix="/contacts", tags=["Contacts & Consent"])


class ContactCreate(BaseModel):
    phone_number: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    tags: Optional[List[str]] = []
    notes: Optional[str] = None
    consent_source: str = "web_form"


class SuppressionCreate(BaseModel):
    phone_number: str
    reason: str = "caller_requested_opt_out"


@router.get("")
def list_contacts(
    search: Optional[str] = None,
    is_suppressed: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Lists contacts with optional keyword filtering and suppression state."""
    q = db.query(Contact).filter(Contact.organization_id == ctx.organization_id)
    if is_suppressed is not None:
        q = q.filter(Contact.is_suppressed == is_suppressed)
    if search:
        s = f"%{search}%"
        q = q.filter(
            (Contact.phone_number.like(s)) |
            (Contact.first_name.like(s)) |
            (Contact.last_name.like(s)) |
            (Contact.email.like(s))
        )

    total = q.count()
    contacts = q.order_by(Contact.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": c.id,
                "phone_number": c.phone_number,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "tags": c.tags or [],
                "notes": c.notes,
                "consent_source": c.consent_source,
                "consent_timestamp": c.consent_timestamp,
                "is_suppressed": c.is_suppressed,
                "created_at": c.created_at,
            }
            for c in contacts
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_contact(
    c_in: ContactCreate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Creates a contact and records lawful calling consent."""
    existing = db.query(Contact).filter(
        Contact.organization_id == ctx.organization_id,
        Contact.phone_number == c_in.phone_number
    ).first()

    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contact already exists with this phone number")

    # Check suppression list
    is_suppressed = db.query(SuppressionEntry).filter(
        SuppressionEntry.organization_id == ctx.organization_id,
        SuppressionEntry.phone_number == c_in.phone_number
    ).first() is not None

    contact = Contact(
        organization_id=ctx.organization_id,
        phone_number=c_in.phone_number,
        first_name=c_in.first_name,
        last_name=c_in.last_name,
        email=c_in.email,
        tags=c_in.tags or [],
        notes=c_in.notes,
        consent_source=c_in.consent_source,
        consent_timestamp=datetime.now(timezone.utc),
        is_suppressed=is_suppressed,
    )
    db.add(contact)
    db.flush()

    # Create consent record
    db.add(ConsentRecord(
        organization_id=ctx.organization_id,
        contact_id=contact.id,
        phone_number=contact.phone_number,
        consent_type="voice_calls",
        consent_source=c_in.consent_source,
        timestamp=datetime.now(timezone.utc)
    ))

    db.commit()
    db.refresh(contact)
    return contact


@router.post("/import-csv")
async def import_contacts_csv(
    file: UploadFile = File(...),
    consent_source: str = "csv_bulk_import",
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """
    Imports contacts from a CSV file.
    Validates phone numbers, checks suppression entries, and reports duplicates and errors.
    """
    content = await file.read()
    decoded = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(decoded))

    created_count = 0
    duplicate_count = 0
    errors = []

    for idx, row in enumerate(reader, start=1):
        phone = row.get("phone") or row.get("phone_number") or row.get("Phone")
        if not phone:
            errors.append(f"Row {idx}: Missing phone number")
            continue

        clean_phone = phone.strip()
        existing = db.query(Contact).filter(
            Contact.organization_id == ctx.organization_id,
            Contact.phone_number == clean_phone
        ).first()

        if existing:
            duplicate_count += 1
            continue

        is_suppressed = db.query(SuppressionEntry).filter(
            SuppressionEntry.organization_id == ctx.organization_id,
            SuppressionEntry.phone_number == clean_phone
        ).first() is not None

        contact = Contact(
            organization_id=ctx.organization_id,
            phone_number=clean_phone,
            first_name=row.get("first_name") or row.get("First Name") or "",
            last_name=row.get("last_name") or row.get("Last Name") or "",
            email=row.get("email") or row.get("Email") or None,
            tags=[t.strip() for t in (row.get("tags") or "").split(",") if t.strip()],
            consent_source=consent_source,
            consent_timestamp=datetime.now(timezone.utc),
            is_suppressed=is_suppressed,
        )
        db.add(contact)
        created_count += 1

    db.commit()
    return {
        "status": "completed",
        "created_count": created_count,
        "duplicate_count": duplicate_count,
        "error_count": len(errors),
        "errors": errors[:10]
    }


@router.post("/suppress")
def suppress_contact(
    sup_in: SuppressionCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Adds a phone number to the Do-Not-Call suppression registry."""
    entry = db.query(SuppressionEntry).filter(
        SuppressionEntry.organization_id == ctx.organization_id,
        SuppressionEntry.phone_number == sup_in.phone_number
    ).first()

    if not entry:
        entry = SuppressionEntry(
            organization_id=ctx.organization_id,
            phone_number=sup_in.phone_number,
            reason=sup_in.reason,
            suppressed_at=datetime.now(timezone.utc)
        )
        db.add(entry)

    # Mark existing contact as suppressed
    contacts = db.query(Contact).filter(
        Contact.organization_id == ctx.organization_id,
        Contact.phone_number == sup_in.phone_number
    ).all()
    for c in contacts:
        c.is_suppressed = True

    db.commit()
    return {"status": "suppressed", "phone_number": sup_in.phone_number}

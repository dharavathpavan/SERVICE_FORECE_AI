import io
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.tenant import Organization, User, OrganizationMembership, OrgRole, AuditLog
from app.models.agent import Agent, AgentVersion, AgentTool
from app.models.knowledge import KnowledgeBase, Document, DocumentChunk
from app.models.telephony import PhoneConnection, Gateway
from app.models.contact import Contact, ConsentRecord
from app.models.campaign import Campaign, CampaignContact
from app.models.call import Call, CallEvent, Transcript
from app.models.billing import UsageRecord, Subscription
from app.services.rag import chunk_text, generate_embedding


# --------------------------------------------------------------------------- #
# Demo logins
# --------------------------------------------------------------------------- #

DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "ServiceForce!2026")

# One account per role, so every RBAC path in the product can be exercised:
#  * owner    — everything, including billing and role changes
#  * admin    — agents, knowledge, telephony, campaigns, contacts, team, audit
#  * manager  — day-to-day operations plus manual outbound calls
#  * operator — read-mostly access plus manual outbound calls
DEMO_USERS: List[Tuple[str, str, OrgRole]] = [
    ("demo.owner@serviceforce.ai", "Dr. Alexander Wright", OrgRole.OWNER),
    ("demo.admin@serviceforce.ai", "Priya Raman", OrgRole.ADMIN),
    ("demo.manager@serviceforce.ai", "Marcus Vance", OrgRole.MANAGER),
    ("demo.agent@serviceforce.ai", "Sofia Alvarez", OrgRole.OPERATOR),
]


def ensure_demo_users(db: Session, org: Organization) -> User:
    """Creates any missing demo logins and corrects their role. Idempotent.

    Returns the owner account so callers can attribute seeded rows to it.
    """
    owner: Optional[User] = None

    for email, full_name, role in DEMO_USERS:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                hashed_password=get_password_hash(DEMO_PASSWORD),
                is_active=True,
                is_superuser=False,
            )
            db.add(user)
            db.flush()

        membership = (
            db.query(OrganizationMembership)
            .filter(
                OrganizationMembership.organization_id == org.id,
                OrganizationMembership.user_id == user.id,
            )
            .first()
        )
        if membership is None:
            db.add(
                OrganizationMembership(
                    organization_id=org.id,
                    user_id=user.id,
                    role=role.value,
                )
            )
        else:
            # Keep an existing demo login aligned with its documented role.
            membership.role = role.value

        if role is OrgRole.OWNER:
            owner = user

    db.flush()
    if owner is None:  # pragma: no cover - guarded by DEMO_USERS
        raise RuntimeError("DEMO_USERS must contain exactly one owner account")
    return owner


def print_demo_logins(org_name: str) -> None:
    print("")
    print(f"Demo logins for '{org_name}'  (password: {DEMO_PASSWORD})")
    print("  " + "-" * 62)
    for email, full_name, role in DEMO_USERS:
        print(f"  {email:<32} {role.value:<9} {full_name}")
    print("  " + "-" * 62)
    print("  Set DEMO_PASSWORD before seeding to use a different password.")


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if already seeded
    existing_org = db.query(Organization).filter(Organization.slug == "apex-healthcare").first()
    if existing_org:
        print("Database already contains Apex Healthcare demo workspace.")
        ensure_demo_users(db, existing_org)
        db.commit()
        print_demo_logins(existing_org.name)
        db.close()
        return

    print("Seeding rich enterprise demonstration workspace...")

    # 1. Organization
    org = Organization(
        name="Apex Care Healthcare",
        slug="apex-healthcare",
        is_active=True,
        billing_plan="professional",
        monthly_call_limit=2500,
    )
    db.add(org)
    db.flush()

    # 2. Demo logins, one per role
    owner = ensure_demo_users(db, org)

    # 3. Knowledge Base
    kb = KnowledgeBase(
        organization_id=org.id,
        name="Apex Clinical Protocols & FAQs",
        description="Official clinical protocols, telemedicine procedures, warranty and prescription refill guidelines.",
    )
    db.add(kb)
    db.flush()

    doc_content = """
    # Apex Care Telehealth Protocols & Guidelines

    ## 1. Appointment Scheduling Policy
    Telehealth video consultations are available Monday through Friday from 08:00 AM to 06:00 PM EST.
    Specialist consultations require at least 24 hours advance reservation. Same-day urgent slots are reserved for triage.

    ## 2. Prescription Refill Procedure
    Maintenance medication refills can be requested autonomously by calling our automated helpline.
    Patients must verify their registered phone number and date of birth. Standard refills are dispatched within 4 hours to the designated pharmacy.

    ## 3. Diagnostic Equipment Warranty & Returns
    All Apex home telemetry monitors (Model X4 and Pro Series) come with an unconditional 3-year replacement warranty.
    Unopened diagnostic test modules can be returned within 30 days of delivery for a 100% refund.

    ## 4. Emergency Escalation Protocol
    If a patient reports acute chest pain, shortness of breath, or emergency symptoms, the voice agent must immediately advise the caller to dial 911 and initiate an immediate warm transfer to our emergency clinical nurse queue at +1-800-555-0199.
    """

    doc = Document(
        organization_id=org.id,
        knowledge_base_id=kb.id,
        title="Apex_Telehealth_Protocols_2026.md",
        file_type="md",
        file_size=len(doc_content.encode("utf-8")),
        status="ready",
    )
    db.add(doc)
    db.flush()

    chunks = chunk_text(doc_content, chunk_size=250, chunk_overlap=30)
    for idx, c in enumerate(chunks):
        vec = generate_embedding(c)
        db.add(DocumentChunk(
            organization_id=org.id,
            knowledge_base_id=kb.id,
            document_id=doc.id,
            chunk_index=idx,
            content=c,
            embedding=vec,
            metadata_json={"title": doc.title, "chunk_index": idx}
        ))
    doc.chunk_count = len(chunks)

    # 4. Primary AI Agent
    agent = Agent(
        organization_id=org.id,
        name="Jordan - Clinical Receptionist",
        purpose="Inbound Triage & Patient Services",
        language="en-US",
        voice="Puck",
        greeting="Thank you for calling Apex Healthcare. My name is Jordan, your AI clinical assistant. How may I help you today?",
        system_prompt="""You are Jordan, an autonomous AI receptionist for Apex Healthcare.
Be warm, calm, empathetic, and concise.
- Look up patient accounts using lookup_customer.
- Track medical equipment shipments using get_order_status.
- Check calendar availability with get_appointment_availability and book slots with create_appointment.
- Reference clinic protocols from attached knowledge bases.
- For emergency symptoms, escalate immediately via request_human_transfer.""",
        fallback_behavior="Apologize and transfer to the senior triage desk.",
        direction="both",
        max_duration_seconds=600,
        human_transfer_number="+1-800-555-0199",
        is_active=True,
        active_version_number=1,
    )
    db.add(agent)
    db.flush()

    db.add(AgentVersion(
        agent_id=agent.id,
        version_number=1,
        prompt_snapshot=agent.system_prompt,
        config_snapshot={"voice": agent.voice, "greeting": agent.greeting},
        notes="Production baseline version",
        created_by_user_id=owner.id,
    ))

    for tool_name in ["lookup_customer", "get_order_status", "check_inventory", "get_appointment_availability", "create_appointment", "request_human_transfer", "end_call"]:
        db.add(AgentTool(agent_id=agent.id, tool_name=tool_name, is_enabled=True))

    # 5. Phone Connection & Gateway
    phone_conn = PhoneConnection(
        organization_id=org.id,
        friendly_name="Apex Primary Patient Hotline",
        phone_number="+1-800-555-0199",
        connection_type="mock",
        is_verified=True,
        health_status="healthy",
        last_health_check=datetime.now(timezone.utc),
        inbound_enabled=True,
        outbound_enabled=True,
        assigned_agent_id=agent.id,
    )
    db.add(phone_conn)

    gw = Gateway(
        organization_id=org.id,
        identifier="GW-APEX-PRIMARY-TRUNK",
        sip_endpoint="sip:trunk.apexcare.internal:5060",
        status="online",
        last_heartbeat=datetime.now(timezone.utc),
        health_details={"latency_ms": 12, "active_channels": 1, "packet_loss": "0.0%"}
    )
    db.add(gw)

    # 6. Sample Contacts
    contacts_data = [
        ("+1-555-0199", "Jane", "Cooper", "jane.c@example.com", ["VIP Patient", "Cardiac Monitor"]),
        ("+1-555-0123", "Marcus", "Vance", "marcus.v@example.com", ["Routine Checkup"]),
        ("+1-555-0177", "Dr. Eleanor", "Vance", "e.vance@example.com", ["Referring Physician"]),
    ]
    created_contacts = []
    for p, fn, ln, em, tg in contacts_data:
        c = Contact(
            organization_id=org.id,
            phone_number=p,
            first_name=fn,
            last_name=ln,
            email=em,
            tags=tg,
            consent_source="patient_portal_optin",
            consent_timestamp=datetime.now(timezone.utc) - timedelta(days=14),
            is_suppressed=False,
        )
        db.add(c)
        db.flush()
        created_contacts.append(c)

    # 7. Outbound Campaign
    camp = Campaign(
        organization_id=org.id,
        name="Weekly Appointment Reminder Campaign",
        agent_id=agent.id,
        status="draft",
        allowed_start_hour="09:00",
        allowed_end_hour="20:00",
        timezone="America/New_York",
        concurrency_limit=2,
        total_contacts=len(created_contacts),
    )
    db.add(camp)
    db.flush()
    for c in created_contacts:
        db.add(CampaignContact(campaign_id=camp.id, contact_id=c.id, status="pending"))

    # 8. Sample Calls with Transcripts
    now = datetime.now(timezone.utc)
    sample_call = Call(
        organization_id=org.id,
        agent_id=agent.id,
        contact_id=created_contacts[0].id,
        direction="inbound",
        phone_number="+1-555-0199",
        caller_id="Jane Cooper",
        status="completed",
        outcome="ai_resolved",
        start_time=now - timedelta(minutes=10),
        end_time=now - timedelta(minutes=8),
        duration_seconds=120,
        summary="Patient called to verify tracking for their Apex Surgical Telehealth Monitor Model X4. Agent confirmed delivery scheduled for tomorrow by 2:00 PM via FedEx Priority.",
        estimated_cost=0.070,
    )
    db.add(sample_call)
    db.flush()

    db.add(CallEvent(call_id=sample_call.id, event_type="speech_start", payload={"speaker": "agent"}))
    db.add(CallEvent(call_id=sample_call.id, event_type="tool_call", payload={"tool": "get_order_status", "order_id": "ORD-8921"}))
    db.add(CallEvent(call_id=sample_call.id, event_type="speech_end", payload={"speaker": "agent"}))

    transcripts = [
        ("agent", "Thank you for calling Apex Healthcare. My name is Jordan, your AI clinical assistant. How may I help you today?", 0, 3200),
        ("caller", "Hi Jordan, I'm checking when my replacement cardiac monitor is arriving.", 3600, 6800),
        ("agent", "I'd be glad to check that for you! May I have your order number or phone number?", 7200, 10500),
        ("caller", "Yes, the order number is ORD-8921.", 11000, 13400),
        ("agent", "Thank you, Jane. I checked order ORD-8921. It has shipped via FedEx Priority and is on schedule for delivery tomorrow by 2:00 PM.", 14000, 22500),
        ("caller", "That's wonderful, thank you so much for your help!", 23000, 25200),
        ("agent", "You're very welcome! Have a wonderful day. Goodbye.", 25600, 28000),
    ]
    for spk, txt, s_ms, e_ms in transcripts:
        db.add(Transcript(call_id=sample_call.id, speaker=spk, text=txt, start_timestamp_ms=s_ms, end_timestamp_ms=e_ms))

    # 9. Usage Record
    db.add(UsageRecord(
        organization_id=org.id,
        call_id=sample_call.id,
        minutes_used=2.0,
        ai_tokens_used=1450,
        cost_cents=7,
        date=now.strftime("%Y-%m-%d"),
    ))

    # 10. Audit Log
    db.add(AuditLog(
        organization_id=org.id,
        user_id=owner.id,
        action="workspace.seeded",
        entity_type="organization",
        entity_id=org.id,
        details={"seed_version": "1.0.0", "name": org.name}
    ))

    db.commit()
    db.close()
    print("Database seeding completed successfully!")
    print_demo_logins("Apex Care Healthcare")


if __name__ == "__main__":
    seed_database()

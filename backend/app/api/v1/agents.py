import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_tenant_context, require_role, TenantContext
from app.models.tenant import OrgRole, AuditLog
from app.models.agent import Agent, AgentVersion, AgentTool
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentDetailResponse,
    AgentVersionResponse,
    AgentTestRequest,
    AgentTestResponse,
)
from app.services.rag import search_knowledge_base

router = APIRouter(prefix="/agents", tags=["AI Agents"])


@router.get("", response_model=List[AgentResponse])
def list_agents(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Lists all AI agents configured for the tenant."""
    return db.query(Agent).filter(Agent.organization_id == ctx.organization_id).all()


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_in: AgentCreate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Creates a new AI Agent with initial version 1."""
    agent = Agent(
        organization_id=ctx.organization_id,
        name=agent_in.name,
        description=agent_in.description,
        purpose=agent_in.purpose,
        language=agent_in.language,
        voice=agent_in.voice,
        greeting=agent_in.greeting,
        system_prompt=agent_in.system_prompt,
        fallback_behavior=agent_in.fallback_behavior,
        direction=agent_in.direction,
        max_duration_seconds=agent_in.max_duration_seconds,
        human_transfer_number=agent_in.human_transfer_number,
        is_active=agent_in.is_active,
        active_version_number=1,
    )
    db.add(agent)
    db.flush()

    # Create initial version 1
    v1 = AgentVersion(
        agent_id=agent.id,
        version_number=1,
        prompt_snapshot=agent.system_prompt,
        config_snapshot={
            "greeting": agent.greeting,
            "voice": agent.voice,
            "language": agent.language,
            "purpose": agent.purpose,
        },
        notes="Initial agent release",
        created_by_user_id=ctx.user.id,
    )
    db.add(v1)

    # Enable default essential tools
    default_tools = ["lookup_customer", "get_order_status", "request_human_transfer", "end_call"]
    for t_name in default_tools:
        db.add(AgentTool(agent_id=agent.id, tool_name=t_name, is_enabled=True))

    audit = AuditLog(
        organization_id=ctx.organization_id,
        user_id=ctx.user.id,
        action="agent.created",
        entity_type="agent",
        entity_id=agent.id,
        details={"agent_name": agent.name}
    )
    db.add(audit)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentDetailResponse)
def get_agent(
    agent_id: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """Retrieves full agent details including versions and enabled tools."""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == ctx.organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    versions = db.query(AgentVersion).filter(AgentVersion.agent_id == agent.id).order_by(AgentVersion.version_number.desc()).all()
    tools = db.query(AgentTool).filter(AgentTool.agent_id == agent.id, AgentTool.is_enabled == True).all()

    return AgentDetailResponse(
        id=agent.id,
        organization_id=agent.organization_id,
        name=agent.name,
        description=agent.description,
        purpose=agent.purpose,
        language=agent.language,
        voice=agent.voice,
        greeting=agent.greeting,
        system_prompt=agent.system_prompt,
        fallback_behavior=agent.fallback_behavior,
        direction=agent.direction,
        max_duration_seconds=agent.max_duration_seconds,
        human_transfer_number=agent.human_transfer_number,
        is_active=agent.is_active,
        active_version_number=agent.active_version_number,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        versions=[AgentVersionResponse.model_validate(v) for v in versions],
        enabled_tools=[t.tool_name for t in tools],
    )


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    agent_in: AgentUpdate,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Updates an agent and creates a new version if prompt or greeting changed."""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == ctx.organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    prompt_changed = (agent_in.system_prompt is not None and agent_in.system_prompt != agent.system_prompt)
    greeting_changed = (agent_in.greeting is not None and agent_in.greeting != agent.greeting)

    update_data = agent_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    # Auto-bump version snapshot if instructions or greeting changed
    if prompt_changed or greeting_changed:
        agent.active_version_number += 1
        new_version = AgentVersion(
            agent_id=agent.id,
            version_number=agent.active_version_number,
            prompt_snapshot=agent.system_prompt,
            config_snapshot={
                "greeting": agent.greeting,
                "voice": agent.voice,
                "language": agent.language,
                "purpose": agent.purpose,
            },
            notes=f"Updated to version {agent.active_version_number}",
            created_by_user_id=ctx.user.id,
        )
        db.add(new_version)

    db.commit()
    db.refresh(agent)
    return agent


@router.post("/{agent_id}/duplicate", response_model=AgentResponse)
def duplicate_agent(
    agent_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Duplicates an existing agent with a new copy suffix."""
    original = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == ctx.organization_id
    ).first()

    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    clone = Agent(
        organization_id=ctx.organization_id,
        name=f"{original.name} (Copy)",
        description=original.description,
        purpose=original.purpose,
        language=original.language,
        voice=original.voice,
        greeting=original.greeting,
        system_prompt=original.system_prompt,
        fallback_behavior=original.fallback_behavior,
        direction=original.direction,
        max_duration_seconds=original.max_duration_seconds,
        human_transfer_number=original.human_transfer_number,
        is_active=False,
        active_version_number=1,
    )
    db.add(clone)
    db.flush()

    v1 = AgentVersion(
        agent_id=clone.id,
        version_number=1,
        prompt_snapshot=clone.system_prompt,
        config_snapshot={"copied_from": original.id},
        notes="Cloned from " + original.name,
        created_by_user_id=ctx.user.id,
    )
    db.add(v1)
    db.commit()
    db.refresh(clone)
    return clone


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: str,
    ctx: TenantContext = Depends(require_role([OrgRole.OWNER.value, OrgRole.ADMIN.value])),
    db: Session = Depends(get_db)
):
    """Deletes an agent."""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == ctx.organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    db.delete(agent)
    db.commit()
    return None


@router.post("/{agent_id}/test", response_model=AgentTestResponse)
def test_agent_playground(
    agent_id: str,
    test_req: AgentTestRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    """
    Agent Playground: Simulates a real-time call turn.
    Performs RAG search across selected knowledge bases, validates tools, and builds response.
    """
    start_time = time.time()
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.organization_id == ctx.organization_id
    ).first()

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    # 1. RAG Retrieval if knowledge bases specified
    retrieved_sources = []
    rag_context_text = ""
    if test_req.knowledge_base_ids:
        for kb_id in test_req.knowledge_base_ids:
            results = search_knowledge_base(
                db=db,
                organization_id=ctx.organization_id,
                query=test_req.message,
                knowledge_base_id=kb_id,
                top_k=2
            )
            for r in results:
                retrieved_sources.append(r)
                rag_context_text += f"\n[Document: {r['document_title']}]: {r['content']}\n"

    # 2. Simulated tool matching based on user query
    tool_calls = []
    user_msg_lower = test_req.message.lower()
    
    if "order" in user_msg_lower:
        tool_calls.append({
            "tool": "get_order_status",
            "parameters": {"order_id": "ORD-8921", "customer_phone": "+1-555-0199"},
            "simulated_result": {"status": "shipped", "carrier": "FedEx", "eta": "Tomorrow by 2:00 PM", "items": 2}
        })
    elif "appointment" in user_msg_lower or "schedule" in user_msg_lower or "book" in user_msg_lower:
        tool_calls.append({
            "tool": "get_appointment_availability",
            "parameters": {"date": "tomorrow", "service": "Consultation"},
            "simulated_result": {"available_slots": ["10:00 AM", "2:30 PM", "4:15 PM"]}
        })
    elif "human" in user_msg_lower or "agent" in user_msg_lower or "representative" in user_msg_lower:
        tool_calls.append({
            "tool": "request_human_transfer",
            "parameters": {"reason": "Customer requested human escalation", "target": agent.human_transfer_number or "+1-800-HUMAN"},
            "simulated_result": {"status": "transfer_initiated", "queue_position": 1}
        })

    # 3. Formulate conversational reply
    if tool_calls and tool_calls[0]["tool"] == "get_order_status":
        reply = "I checked order ORD-8921 for you. It has shipped via FedEx and is scheduled for delivery tomorrow by 2:00 PM."
    elif tool_calls and tool_calls[0]["tool"] == "get_appointment_availability":
        reply = "I see three available consultation slots tomorrow: 10:00 AM, 2:30 PM, and 4:15 PM. Which time works best for you?"
    elif tool_calls and tool_calls[0]["tool"] == "request_human_transfer":
        reply = f"Certainly! Let me transfer you right away to our senior specialist at {agent.human_transfer_number or 'our escalation line'}. Please hold for just a moment."
    elif retrieved_sources:
        top_src = retrieved_sources[0]
        reply = f"According to our {top_src['document_title']}: {top_src['content'][:220]}... Let me know if you need more details!"
    else:
        reply = f"Thank you for contacting us. I am {agent.name}, your automated assistant. Regarding '{test_req.message}', how can I assist you further today?"

    elapsed_ms = (time.time() - start_time) * 1000

    return AgentTestResponse(
        reply=reply,
        tool_calls=tool_calls,
        retrieved_sources=retrieved_sources,
        latency_ms=round(elapsed_ms, 2),
        simulated_speech_ready=True,
    )

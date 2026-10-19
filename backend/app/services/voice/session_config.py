"""
Translate stored agent configuration into a provider session config.

The provider layer must not import our ORM, and the WebSocket handler should not
carry business mapping, so this module owns the single job of turning a call plus
the agent it is bound to into :class:`VoiceSessionConfig`.

It is a pure set of database reads, which keeps it directly testable without
opening a socket.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent import Agent, AgentTool
from app.models.call import Call
from app.services.voice.provider import VoiceSessionConfig

# Used only when a call has no agent bound, so the audio bridge can still start.
FALLBACK_AGENT_NAME = "ServiceForce Agent"
FALLBACK_SYSTEM_PROMPT = (
    "You are a concise, helpful phone agent. Answer in one or two short sentences."
)
FALLBACK_GREETING = "Hello, thanks for calling. How can I help?"
FALLBACK_VOICE = "Puck"
FALLBACK_LANGUAGE = "en-US"


def enabled_agent_tools(db: Session, agent_id: str) -> List[Dict[str, Any]]:
    """Tools the agent is allowed to call, in the shape the provider expects."""
    tools = (
        db.query(AgentTool)
        .filter(AgentTool.agent_id == agent_id, AgentTool.is_enabled.is_(True))
        .all()
    )
    return [{"name": tool.tool_name, "config": dict(tool.config or {})} for tool in tools]


def build_voice_config(db: Session, call: Call) -> VoiceSessionConfig:
    """Assemble the provider config for ``call`` from its agent, if any."""
    agent: Optional[Agent] = None
    if call.agent_id:
        agent = (
            db.query(Agent)
            .filter(
                Agent.id == call.agent_id,
                Agent.organization_id == call.organization_id,
            )
            .first()
        )

    return VoiceSessionConfig(
        call_id=call.id,
        agent_name=agent.name if agent else FALLBACK_AGENT_NAME,
        system_prompt=(
            agent.system_prompt if agent and agent.system_prompt else FALLBACK_SYSTEM_PROMPT
        ),
        greeting=agent.greeting if agent and agent.greeting else FALLBACK_GREETING,
        voice=agent.voice if agent and agent.voice else FALLBACK_VOICE,
        language=agent.language if agent and agent.language else FALLBACK_LANGUAGE,
        tools=enabled_agent_tools(db, agent.id) if agent else [],
        context={
            "phone_number": call.phone_number,
            "direction": call.direction,
            "agent_id": call.agent_id,
        },
    )

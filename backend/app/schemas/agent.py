from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AgentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    purpose: str = "Customer Support"
    language: str = "en-US"
    voice: str = "Puck"
    greeting: str
    system_prompt: str
    fallback_behavior: str = "Apologize and offer human transfer."
    direction: str = "both"  # inbound, outbound, both
    max_duration_seconds: int = Field(600, ge=30, le=3600)
    human_transfer_number: Optional[str] = None
    is_active: bool = True


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    language: Optional[str] = None
    voice: Optional[str] = None
    greeting: Optional[str] = None
    system_prompt: Optional[str] = None
    fallback_behavior: Optional[str] = None
    direction: Optional[str] = None
    max_duration_seconds: Optional[int] = None
    human_transfer_number: Optional[str] = None
    is_active: Optional[bool] = None


class AgentVersionResponse(BaseModel):
    id: str
    agent_id: str
    version_number: int
    prompt_snapshot: str
    config_snapshot: Dict[str, Any]
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentResponse(AgentBase):
    id: str
    organization_id: str
    active_version_number: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentDetailResponse(AgentResponse):
    versions: List[AgentVersionResponse] = []
    enabled_tools: List[str] = []


class AgentTestRequest(BaseModel):
    message: str
    knowledge_base_ids: Optional[List[str]] = []
    enable_tools: Optional[bool] = True
    context: Optional[Dict[str, Any]] = {}


class AgentTestResponse(BaseModel):
    reply: str
    tool_calls: List[Dict[str, Any]] = []
    retrieved_sources: List[Dict[str, Any]] = []
    latency_ms: float
    simulated_speech_ready: bool

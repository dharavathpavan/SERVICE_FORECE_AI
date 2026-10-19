"""
Voice provider interface.

Separates *speech transport and model interaction* from conversation
orchestration, knowledge retrieval and tool execution. The API/worker layers
depend on this interface, never on a vendor SDK.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional


class VoiceProviderError(Exception):
    code = "voice_provider_error"
    user_message = "The voice provider is unavailable."

    def __init__(self, message: Optional[str] = None, *, details: Optional[Dict[str, Any]] = None):
        super().__init__(message or self.user_message)
        self.message = message or self.user_message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"error": self.code, "message": self.user_message, "details": self.details}


class VoiceProviderUnavailable(VoiceProviderError):
    code = "voice_provider_unavailable"
    user_message = "No real-time voice provider is configured. Set VOICE_PROVIDER and credentials."


class VoiceProviderAuthError(VoiceProviderError):
    code = "voice_provider_auth_error"
    user_message = "The voice provider rejected the configured credentials."


class VoiceEventType(str, Enum):
    AUDIO_OUT = "audio_out"          # model audio to play to the caller
    TRANSCRIPT = "transcript"        # interim/final speech-to-text or model text
    TOOL_CALL = "tool_call"          # model requests a business tool
    INTERRUPTED = "interrupted"      # barge-in acknowledged
    TURN_END = "turn_end"
    ERROR = "error"
    END = "end"


@dataclass
class VoiceEvent:
    type: VoiceEventType
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type.value, **self.data}


@dataclass
class VoiceSessionConfig:
    """Everything the provider needs to open a session for one call."""

    call_id: str
    agent_name: str
    system_prompt: str
    greeting: str
    voice: str = "Puck"
    language: str = "en-US"
    tools: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    input_sample_rate: int = 16000
    output_sample_rate: int = 24000
    barge_in_enabled: bool = True


class VoiceSession(abc.ABC):
    """A single live conversation over the audio bridge."""

    @abc.abstractmethod
    async def start(self) -> None:
        """(Re)configure the model session and prepare to receive audio."""

    @abc.abstractmethod
    async def send_audio(self, chunk: bytes) -> None:
        """Push a chunk of caller audio (PCM16) to the provider."""

    @abc.abstractmethod
    async def receive(self) -> VoiceEvent:
        """Await the next provider event (audio, transcript, tool call, end)."""

    @abc.abstractmethod
    async def interrupt(self) -> None:
        """Barge-in: stop the model's current output immediately."""

    @abc.abstractmethod
    async def send_tool_result(self, tool_name: str, result: Dict[str, Any]) -> None:
        """Return a business-tool result into the conversation."""

    @abc.abstractmethod
    async def end(self) -> None:
        """Close the session and release resources."""


class VoiceProvider(abc.ABC):
    """Factory for :class:`VoiceSession` objects, plus capability reporting."""

    name: str = "abstract"

    @abc.abstractmethod
    def create_session(self, config: VoiceSessionConfig) -> VoiceSession:
        """Create a session. Must not perform network I/O yet (call ``start``)."""

    @abc.abstractmethod
    def capabilities(self) -> Dict[str, Any]:
        """Report supported features: streaming audio, barge-in, tool calling, etc."""

    def is_configured(self) -> bool:
        """Whether the provider has the credentials/endpoint it needs."""
        return True

"""
Gemini Live voice provider (server-side only).

Security: the API key is read from settings on the server and is never sent to any
client. Browsers only ever see the ServiceForce WebSocket, not the vendor endpoint.

Honesty: if no API key is configured the provider reports itself unavailable and
``create_session`` raises :class:`VoiceProviderUnavailable` rather than pretending
to work. The exact Live wire protocol is versioned upstream — verify the endpoint
and message schema against current Google documentation before production use
(see ``capabilities()['notes']``).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import websockets

from app.core.config import settings
from app.services.voice.provider import (
    VoiceEvent,
    VoiceEventType,
    VoiceProvider,
    VoiceProviderAuthError,
    VoiceProviderUnavailable,
    VoiceSession,
    VoiceSessionConfig,
)

logger = logging.getLogger(__name__)

# NOTE: verify against current Google documentation before enabling in production.
GEMINI_LIVE_ENDPOINT = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)


class GeminiLiveSession(VoiceSession):
    def __init__(self, config: VoiceSessionConfig, api_key: str, endpoint: str) -> None:
        self.config = config
        self.api_key = api_key
        self.endpoint = endpoint
        self._ws: Optional[Any] = None
        self._recv_queue: asyncio.Queue = asyncio.Queue()
        self._pump_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        url = f"{self.endpoint}?key={self.api_key}"
        try:
            self._ws = await websockets.connect(url, max_size=None)
        except Exception as exc:  # network/auth failure — surface honestly
            raise VoiceProviderUnavailable(f"Could not open Gemini Live socket: {exc}") from exc

        setup = {
            "setup": {
                "model": f"models/{settings.GEMINI_LIVE_MODEL}",
                "generation_config": {"response_modalities": ["AUDIO"]},
                "system_instruction": {"parts": [{"text": self.config.system_prompt}]},
                # Speak with the voice/language configured on the agent.
                "speech_config": {
                    "language_code": self.config.language,
                    "voice_config": {
                        "prebuilt_voice_config": {"voice_name": self.config.voice}
                    },
                },
            }
        }
        await self._ws.send(json.dumps(setup))
        self._pump_task = asyncio.create_task(self._pump())

    async def _pump(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                event = self._translate(msg)
                if event:
                    await self._recv_queue.put(event)
        except Exception as exc:  # pragma: no cover - network dependent
            await self._recv_queue.put(VoiceEvent(VoiceEventType.ERROR, {"message": str(exc)}))
        finally:
            await self._recv_queue.put(VoiceEvent(VoiceEventType.END, {}))

    def _translate(self, msg: Dict[str, Any]) -> Optional[VoiceEvent]:
        """Map a vendor message to a neutral VoiceEvent. Extend as the API evolves."""
        if "serverContent" in msg:
            content = msg["serverContent"]
            if content.get("interrupted"):
                return VoiceEvent(VoiceEventType.INTERRUPTED, {})
            if content.get("turnComplete"):
                return VoiceEvent(VoiceEventType.TURN_END, {})
            parts = (content.get("modelTurn") or {}).get("parts") or []
            for part in parts:
                if "inlineData" in part:
                    inline = part["inlineData"]
                    return VoiceEvent(
                        VoiceEventType.AUDIO_OUT,
                        {
                            "mime": inline.get("mimeType"),
                            "audio": inline.get("data"),
                            "encoding": "pcm16",
                        },
                    )
                if "text" in part:
                    return VoiceEvent(VoiceEventType.TRANSCRIPT, {"speaker": "agent", "text": part["text"]})
        if "toolCall" in msg:
            calls = msg["toolCall"].get("functionCalls") or []
            if calls:
                first = calls[0]
                return VoiceEvent(
                    VoiceEventType.TOOL_CALL,
                    {"tool": first.get("name"), "arguments": first.get("args", {})},
                )
        return None

    async def send_audio(self, chunk: bytes) -> None:
        if not self._ws:
            raise VoiceProviderUnavailable("Session not started.")
        import base64

        await self._ws.send(
            json.dumps(
                {
                    "realtimeInput": {
                        "mediaChunks": [
                            {
                                "mimeType": f"audio/pcm;rate={self.config.input_sample_rate}",
                                "data": base64.b64encode(chunk).decode(),
                            }
                        ]
                    }
                }
            )
        )

    async def receive(self) -> VoiceEvent:
        return await self._recv_queue.get()

    async def interrupt(self) -> None:
        if self._ws:
            try:
                await self._ws.send(json.dumps({"clientContent": {"turnComplete": False, "interrupted": True}}))
            except Exception:  # pragma: no cover
                pass

    async def send_tool_result(self, tool_name: str, result: Dict[str, Any]) -> None:
        if not self._ws:
            return
        await self._ws.send(
            json.dumps(
                {
                    "toolResponse": {
                        "functionResponses": [
                            {"name": tool_name, "response": {"result": result}}
                        ]
                    }
                }
            )
        )

    async def end(self) -> None:
        if self._pump_task:
            self._pump_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:  # pragma: no cover
                pass


class GeminiLiveProvider(VoiceProvider):
    name = "gemini_live"

    def __init__(self, api_key: Optional[str] = None, endpoint: str = GEMINI_LIVE_ENDPOINT) -> None:
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.endpoint = endpoint

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def create_session(self, config: VoiceSessionConfig) -> VoiceSession:
        if not self.is_configured():
            raise VoiceProviderUnavailable(
                "GEMINI_API_KEY is not set; cannot create a Gemini Live session."
            )
        return GeminiLiveSession(config, self.api_key, self.endpoint)

    def capabilities(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "streaming_audio": True,
            "bidirectional": True,
            "barge_in": True,
            "tool_calling": True,
            "native_audio": True,
            "configured": self.is_configured(),
            "notes": [
                "Server-side only; the API key never reaches clients.",
                "Verify the Live endpoint and message schema against current Google docs.",
                f"Model: {settings.GEMINI_LIVE_MODEL}",
            ],
        }

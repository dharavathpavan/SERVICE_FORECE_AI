"""
Deterministic mock voice provider.

Used when no real speech provider is configured. It generates a believable turn
sequence (greeting → caller turn → tool call → response) and honours barge-in, so
the full call pipeline can be exercised without network access or API keys.

Unlike a silent stub, the agent turns carry playable PCM16: each scripted sentence
is rendered locally by :mod:`app.services.voice.synthesis` (Windows system speech
when available, speech-shaped tones otherwise). The engine that ran is reported in
``capabilities()["audio_engine"]`` - the mock never pretends it produced model audio.
"""
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.voice.provider import (
    VoiceEvent,
    VoiceEventType,
    VoiceProvider,
    VoiceSession,
    VoiceSessionConfig,
)
from app.services.voice.synthesis import (
    engine_report,
    synthesize,
    wav_to_pcm16,
)

logger = logging.getLogger(__name__)

CALLER_LINE = "I'd like to check my order status."
AGENT_REPLY = "Your order ORD-8921 shipped and arrives tomorrow by 2 PM."


class MockVoiceSession(VoiceSession):
    def __init__(self, config: VoiceSessionConfig) -> None:
        self.config = config
        self._outbox: asyncio.Queue = asyncio.Queue()
        self._scripted: List[VoiceEvent] = []
        self._interrupted = False
        self._turn = 0
        self._ended = False

    async def start(self) -> None:
        self._scripted = self._build_script()
        await self._attach_audio()

    def _build_script(self) -> List[VoiceEvent]:
        tool = next((t for t in self.config.tools if t.get("name") == "get_order_status"), None)
        events: List[VoiceEvent] = [
            VoiceEvent(
                VoiceEventType.TRANSCRIPT,
                {"speaker": "agent", "text": self.config.greeting, "final": True},
            ),
            VoiceEvent(VoiceEventType.AUDIO_OUT, {"speech": self.config.greeting}),
            VoiceEvent(
                VoiceEventType.TRANSCRIPT,
                {"speaker": "caller", "text": CALLER_LINE, "final": True},
            ),
        ]
        if tool:
            events.append(
                VoiceEvent(
                    VoiceEventType.TOOL_CALL,
                    {"tool": "get_order_status", "arguments": {"order_id": "ORD-8921"}},
                )
            )
        events.append(
            VoiceEvent(
                VoiceEventType.TRANSCRIPT,
                {"speaker": "agent", "text": AGENT_REPLY, "final": True},
            )
        )
        events.append(VoiceEvent(VoiceEventType.AUDIO_OUT, {"speech": AGENT_REPLY}))
        events.append(VoiceEvent(VoiceEventType.TURN_END, {}))
        return events

    async def _attach_audio(self) -> None:
        """
        Replace every scripted agent line with locally generated PCM16.

        Synthesis is best-effort: if no engine can render a sentence the event still
        goes out (without audio) and the transcripts remain the authoritative record.
        """
        targets = [event for event in self._scripted if event.type == VoiceEventType.AUDIO_OUT]
        if not targets:
            return

        sentences = [str(event.data.get("speech") or "") for event in targets]
        try:
            rendered = await asyncio.to_thread(
                synthesize,
                sentences,
                sample_rate=self.config.output_sample_rate,
                preferred=settings.VOICE_MOCK_TTS,
            )
        except Exception:  # a missing/broken speech engine must not kill the call
            logger.exception("Mock speech synthesis failed; continuing without audio.")
            rendered = [None for _ in sentences]

        for event, wav in zip(targets, rendered):
            event.data.pop("speech", None)
            if not wav:
                event.data["note"] = "no audio engine available"
                continue
            try:
                pcm, rate = wav_to_pcm16(wav)
            except Exception:
                logger.exception("Generated audio was not a readable WAV.")
                event.data["note"] = "audio could not be decoded"
                continue
            event.data.update(
                {
                    "audio": base64.b64encode(pcm).decode("ascii"),
                    "encoding": "pcm16",
                    "channels": 1,
                    "sample_rate": rate,
                }
            )

    async def send_audio(self, chunk: bytes) -> None:
        # Simulate the caller speaking: on the first audio chunk, advance one turn.
        if self._ended:
            return
        if self._turn == 0 and chunk:
            self._turn = 1

    async def receive(self) -> VoiceEvent:
        if self._interrupted:
            self._interrupted = False
            return VoiceEvent(VoiceEventType.INTERRUPTED, {"latency_ms": 180})
        if self._scripted:
            return self._scripted.pop(0)
        if not self._outbox.empty():
            return await self._outbox.get()
        if self._ended:
            return VoiceEvent(VoiceEventType.END, {})
        # Nothing left: block briefly to mimic a quiet line, then end.
        await asyncio.sleep(0)
        return VoiceEvent(VoiceEventType.END, {"reason": "script_complete"})

    async def interrupt(self) -> None:
        self._interrupted = True
        self._scripted = [e for e in self._scripted if e.type == VoiceEventType.TRANSCRIPT]

    async def send_tool_result(self, tool_name: str, result: Dict[str, Any]) -> None:
        await self._outbox.put(
            VoiceEvent(VoiceEventType.TRANSCRIPT, {"speaker": "system", "text": f"{tool_name} → ok", "final": True})
        )

    async def end(self) -> None:
        self._ended = True


class MockVoiceProvider(VoiceProvider):
    name = "mock"

    def create_session(self, config: VoiceSessionConfig) -> VoiceSession:
        return MockVoiceSession(config)

    def capabilities(self) -> Dict[str, Any]:
        report = engine_report(settings.VOICE_MOCK_TTS)
        return {
            "provider": self.name,
            "streaming_audio": True,
            "bidirectional": True,
            "barge_in": True,
            "tool_calling": True,
            # Not model-native audio: this provider renders a fixed script locally.
            "native_audio": False,
            "configured": True,
            "audio_engine": report,
            "notes": [
                "Simulation provider; no external model calls.",
                f"Agent turns are synthesized locally ({report['engine']}).",
            ],
        }


mock_voice_provider = MockVoiceProvider()

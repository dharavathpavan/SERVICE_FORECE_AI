"""The simulated voice provider must produce audio you can actually play.

A mock is allowed to be a simulation, but it should not be a silent one. Every agent
turn now carries locally synthesized PCM16, the audio bridge stores what the agent
said, and the dashboard can stream it back. These tests pin down:

  * the audio format (16-bit, mono, WAV at the requested rate),
  * that the engine actually produced a non-silent signal,
  * that the provider reports truthfully *which* engine ran,
  * that the served artifact is tenant-scoped and never claims to be a call recording.
"""
from __future__ import annotations

import asyncio
import base64
import io
import time
import wave

import pytest

from app.core.config import settings
from app.models.call import Call
from app.models.agent import Agent, AgentTool
from app.models.telephony import PhoneConnection
from app.services.storage import set_storage
from app.services.telephony import factory
from app.services.telephony.mock_adapter import MockTelephonyAdapter
from app.services.voice import synthesis
from app.services.voice.mock_provider import MockVoiceProvider
from app.services.voice.provider import VoiceEventType, VoiceSessionConfig

DID = "+1-800-555-0177"
GREETING = "Hi, this is Dana from the billing team."


def _wav_info(data: bytes) -> dict:
    with wave.open(io.BytesIO(data), "rb") as handle:
        return {
            "channels": handle.getnchannels(),
            "width": handle.getsampwidth(),
            "rate": handle.getframerate(),
            "frames": handle.getnframes(),
        }


def _peak_amplitude(wav_bytes: bytes) -> int:
    import numpy as np

    with wave.open(io.BytesIO(wav_bytes), "rb") as handle:
        samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
    return int(np.max(np.abs(samples))) if samples.size else 0


@pytest.fixture(autouse=True)
def portable_speech_and_temp_storage(tmp_path, monkeypatch):
    """Keep the suite fast, deterministic and out of the repository."""
    monkeypatch.setattr(settings, "VOICE_MOCK_TTS", "tones")
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "STORAGE_LOCAL_PATH", str(tmp_path / "objects"))
    set_storage(None)
    yield
    set_storage(None)


@pytest.fixture(autouse=True)
def mock_telephony():
    factory.set_adapter(MockTelephonyAdapter())
    yield
    factory.set_adapter(None)


# --------------------------------------------------------------------------- #
# Synthesis
# --------------------------------------------------------------------------- #
def test_synthesis_returns_a_mono_16khz_wav():
    [clip] = synthesis.synthesize(
        ["Your order shipped and arrives tomorrow."], sample_rate=16000, preferred="tones"
    )

    info = _wav_info(clip)
    assert info["channels"] == 1
    assert info["width"] == 2
    assert info["rate"] == 16000
    # Speech-paced, not a click.
    assert info["frames"] / info["rate"] > 0.3


def test_longer_text_produces_longer_audio():
    short = _wav_info(synthesis.synthesize(["Yes."], sample_rate=16000, preferred="tones")[0])
    long = _wav_info(
        synthesis.synthesize(
            ["Yes, I can confirm that your replacement order shipped this morning."],
            sample_rate=16000,
            preferred="tones",
        )[0]
    )

    assert long["frames"] > short["frames"]


def test_tones_engine_is_audible():
    [clip] = synthesis.synthesize(["Hello there, how can I help?"], sample_rate=16000, preferred="tones")

    # A silent file would make the whole "the AI talks" claim hollow.
    assert _peak_amplitude(clip) > 3000


def test_synthesis_requests_any_sample_rate():
    [clip] = synthesis.synthesize(["Testing the line."], sample_rate=24000, preferred="tones")

    assert _wav_info(clip)["rate"] == 24000


@pytest.mark.skipif(
    not synthesis.system_engine_available(),
    reason="Windows system speech is not available on this platform",
)
def test_system_engine_produces_intelligible_speech_marked_as_such():
    [clip] = synthesis.synthesize(["Your order arrives tomorrow."], sample_rate=16000, preferred="system")

    info = _wav_info(clip)
    assert info["channels"] == 1
    assert info["width"] == 2
    assert info["frames"] > 0
    assert _peak_amplitude(clip) > 3000
    assert synthesis.active_engine("system") == synthesis.ENGINE_SYSTEM
    assert synthesis.engine_report("system")["intelligible"] is True


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #
def _drain(session) -> list:
    async def run() -> list:
        await session.start()
        events = []
        while True:
            event = await session.receive()
            events.append(event)
            if event.type == VoiceEventType.END:
                return events

    return asyncio.run(run())


def _session() -> object:
    config = VoiceSessionConfig(
        call_id="mock-audio-call",
        agent_name="Billing Agent",
        system_prompt="Handle billing questions.",
        greeting=GREETING,
        output_sample_rate=24000,
        tools=[{"name": "get_order_status", "config": {}}],
    )
    return MockVoiceProvider().create_session(config)


def test_agent_turns_carry_playable_pcm():
    events = _drain(_session())

    audio_events = [event for event in events if event.type == VoiceEventType.AUDIO_OUT]
    assert len(audio_events) == 2, "the greeting and the answer should both be spoken"

    for event in audio_events:
        assert event.data["encoding"] == "pcm16"
        assert event.data["channels"] == 1
        assert event.data["sample_rate"] == 24000
        pcm = base64.b64decode(event.data["audio"])
        assert len(pcm) % 2 == 0
        assert len(pcm) > 4800, "expected more than 100ms of audio per agent turn"


def test_the_greeting_is_spoken_and_transcribed_first():
    events = _drain(_session())

    spoken = [e for e in events if e.type == VoiceEventType.TRANSCRIPT]
    assert spoken[0].data["text"] == GREETING
    assert spoken[0].data["speaker"] == "agent"
    # The greeting transcript precedes the audio for it, so a recording built from
    # AUDIO_OUT events lines up with the transcript order.
    assert events[0].type == VoiceEventType.TRANSCRIPT
    assert events[1].type == VoiceEventType.AUDIO_OUT


def test_audio_is_still_recorded_when_no_tool_is_enabled():
    config = VoiceSessionConfig(
        call_id="c", agent_name="a", system_prompt="p", greeting="Hello.", output_sample_rate=16000
    )
    events = _drain(MockVoiceProvider().create_session(config))

    audio_events = [e for e in events if e.type == VoiceEventType.AUDIO_OUT]
    assert len(audio_events) == 2
    assert all(event.data.get("audio") for event in audio_events)


def test_capabilities_state_that_the_audio_is_synthesized():
    caps = MockVoiceProvider().capabilities()

    assert caps["native_audio"] is False  # never claim model audio
    assert caps["audio_engine"]["engine"] == synthesis.ENGINE_TONES
    assert caps["audio_engine"]["intelligible"] is False
    assert any("synthesized" in note for note in caps["notes"])


# --------------------------------------------------------------------------- #
# End-to-end: bridge -> storage -> authenticated endpoint
# --------------------------------------------------------------------------- #
@pytest.fixture()
def org(client):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": "audio-owner@example.com",
            "full_name": "Audio Owner",
            "password": "Password123!",
            "organization_name": "Audio Co",
        },
    ).json()


@pytest.fixture()
def agent(db_session, org):
    agent = Agent(
        organization_id=org["organization_id"],
        name="Billing Agent",
        greeting=GREETING,
        system_prompt="Handle billing questions.",
        direction="both",
        is_active=True,
    )
    db_session.add(agent)
    db_session.flush()
    db_session.add(AgentTool(agent_id=agent.id, tool_name="get_order_status", is_enabled=True))
    db_session.commit()
    db_session.refresh(agent)
    return agent


def _connection(org, agent) -> PhoneConnection:
    """A verified inbound line with the agent bound to it."""
    return PhoneConnection(
        organization_id=org["organization_id"],
        friendly_name="Main line",
        phone_number=DID,
        connection_type="gsm_gateway",
        is_verified=True,
        health_status="healthy",
        inbound_enabled=True,
        outbound_enabled=True,
        assigned_agent_id=agent.id,
    )


def test_bridge_stores_agent_audio_and_serves_it_to_the_tenant(client, db_session, org, agent):
    db_session.add(_connection(org, agent))
    db_session.commit()

    inbound = client.post(
        "/api/v1/telephony/inbound",
        json={"call_id": "mock-audio-inbound-1", "from_number": "+1-555-0199", "to_number": DID},
    )
    assert inbound.status_code == 200, inbound.text
    call_id = inbound.json()["call_id"]

    audio_frames = 0
    with client.websocket_connect(
        f"/api/v1/voice/stream?call_id={call_id}&token={org['access_token']}"
    ) as ws:
        for _ in range(7):
            message = ws.receive_json()
            if message.get("type") == "audio_out" and message.get("audio"):
                audio_frames += 1
    assert audio_frames == 2, "both agent turns should arrive as audio over the bridge"

    call = None
    for _ in range(40):
        db_session.expire_all()
        call = db_session.query(Call).filter(Call.id == call_id).first()
        if call is not None and call.agent_audio_key:
            break
        time.sleep(0.05)

    assert call is not None and call.agent_audio_key, "the bridge should store the agent audio"
    assert call.agent_audio_key.startswith(org["organization_id"])
    assert call.recording_url is None, "the mock carrier records nothing; do not pretend it did"

    detail = client.get(
        f"/api/v1/calls/{call_id}", headers={"Authorization": f"Bearer {org['access_token']}"}
    ).json()
    assert detail["agent_audio_url"] == f"/api/v1/calls/{call_id}/agent-audio"
    assert detail["recording_url"] is None

    audio = client.get(
        f"/api/v1/calls/{call_id}/agent-audio",
        headers={"Authorization": f"Bearer {org['access_token']}"},
    )
    assert audio.status_code == 200, audio.text
    assert audio.headers["content-type"].startswith("audio/wav")
    info = _wav_info(audio.content)
    assert info["channels"] == 1
    assert info["width"] == 2
    assert info["rate"] == 24000
    assert info["frames"] / info["rate"] > 0.5, "the agent's greeting plus answer"


def test_agent_audio_is_not_served_across_tenants(client, db_session, org, agent):
    db_session.add(_connection(org, agent))
    db_session.commit()

    inbound = client.post(
        "/api/v1/telephony/inbound",
        json={"call_id": "mock-audio-inbound-2", "from_number": "+1-555-0199", "to_number": DID},
    )
    call_id = inbound.json()["call_id"]

    with client.websocket_connect(
        f"/api/v1/voice/stream?call_id={call_id}&token={org['access_token']}"
    ) as ws:
        for _ in range(7):
            ws.receive_json()

    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "nosy@example.com",
            "full_name": "Nosy",
            "password": "Password123!",
            "organization_name": "Nosy Co",
        },
    ).json()

    resp = client.get(
        f"/api/v1/calls/{call_id}/agent-audio",
        headers={"Authorization": f"Bearer {other['access_token']}"},
    )
    assert resp.status_code == 404

    unauthenticated = client.get(f"/api/v1/calls/{call_id}/agent-audio")
    assert unauthenticated.status_code in (401, 403)


def test_a_call_without_audio_says_so(client, db_session, org):
    call = Call(
        organization_id=org["organization_id"],
        direction="outbound",
        phone_number="+1-555-0100",
        status="failed",
        outcome="failed",
    )
    db_session.add(call)
    db_session.commit()

    resp = client.get(
        f"/api/v1/calls/{call.id}/agent-audio",
        headers={"Authorization": f"Bearer {org['access_token']}"},
    )
    assert resp.status_code == 404
    assert "no stored agent audio" in resp.json()["detail"].lower()

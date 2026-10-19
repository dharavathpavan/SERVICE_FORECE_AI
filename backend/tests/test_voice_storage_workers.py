"""Tests for voice provider, storage backends and worker tasks (M5, M6)."""
import asyncio
import os

import pytest

from app.services.storage.factory import build_storage, set_storage
from app.services.storage.local import LocalStorage
from app.services.storage.base import StorageError, build_key
from app.services.voice.factory import (
    build_voice_provider,
    get_voice_provider,
    UnknownVoiceProvider,
)
from app.services.voice.gemini_live import GeminiLiveProvider
from app.services.voice.mock_provider import MockVoiceProvider
from app.services.voice.provider import VoiceEventType, VoiceProviderUnavailable, VoiceSessionConfig
from app.services.workers.runner import InlineRunner
from app.services.workers import tasks


# --------------------------------------------------------------------------- #
# Voice provider
# --------------------------------------------------------------------------- #
def test_voice_factory_mock_default():
    provider = build_voice_provider("mock")
    assert isinstance(provider, MockVoiceProvider)
    caps = provider.capabilities()
    assert caps["streaming_audio"] is True
    assert caps["barge_in"] is True


def test_voice_factory_gemini_requires_key():
    provider = GeminiLiveProvider(api_key="")
    assert provider.is_configured() is False
    with pytest.raises(VoiceProviderUnavailable):
        provider.create_session(
            VoiceSessionConfig(call_id="c", agent_name="a", system_prompt="s", greeting="hi")
        )


def test_voice_factory_rejects_unknown_provider():
    with pytest.raises(UnknownVoiceProvider):
        build_voice_provider("ultravox")


def test_get_voice_provider_falls_back_when_unconfigured(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "VOICE_PROVIDER", "gemini_live", raising=False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "", raising=False)
    provider = get_voice_provider()
    assert provider.name == "mock"


def test_mock_voice_session_turn_sequence():
    provider = MockVoiceProvider()
    config = VoiceSessionConfig(
        call_id="c1",
        agent_name="Agent",
        system_prompt="be helpful",
        greeting="Hello!",
        tools=[{"name": "get_order_status"}],
    )

    async def run():
        session = provider.create_session(config)
        await session.start()
        events = []
        for _ in range(8):
            event = await session.receive()
            events.append(event.type)
            if event.type == VoiceEventType.END:
                break
        return events

    events = asyncio.run(run())
    assert VoiceEventType.TRANSCRIPT in events
    assert VoiceEventType.TOOL_CALL in events
    assert VoiceEventType.TURN_END in events


def test_mock_voice_barge_in():
    provider = MockVoiceProvider()

    async def run():
        session = provider.create_session(
            VoiceSessionConfig(call_id="c", agent_name="a", system_prompt="s", greeting="hi")
        )
        await session.start()
        await session.interrupt()
        event = await session.receive()
        return event.type

    assert asyncio.run(run()) == VoiceEventType.INTERRUPTED


def test_voice_capabilities_endpoint(client):
    resp = client.get("/api/v1/voice/capabilities")
    assert resp.status_code == 200
    assert resp.json()["provider"] == "mock"


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
def test_local_storage_roundtrip(tmp_path):
    storage = LocalStorage(str(tmp_path / "objects"))
    key = build_key("org-1", "recordings", "call-1.wav")
    uri = storage.put(key, b"audio-bytes", content_type="audio/wav")
    assert uri.startswith("file://")
    assert storage.exists(key) is True
    assert storage.get(key) == b"audio-bytes"
    storage.delete(key)
    assert storage.exists(key) is False


def test_local_storage_rejects_path_traversal(tmp_path):
    storage = LocalStorage(str(tmp_path))
    with pytest.raises(StorageError):
        storage.put("../../etc/passwd", b"x")


def test_build_key_is_tenant_scoped():
    assert build_key("org-9", "docs", "policy.pdf") == "org-9/docs/policy.pdf"


def test_storage_factory_rejects_unknown_backend(monkeypatch):
    from app.services.storage import factory

    set_storage(None)
    with pytest.raises(StorageError):
        factory.build_storage("ftp")
    set_storage(None)


# --------------------------------------------------------------------------- #
# Workers
# --------------------------------------------------------------------------- #
def test_ingest_document_chunks_and_embeds(db_session, org_factory):
    org = org_factory()
    from app.models.knowledge import Document, KnowledgeBase

    kb = KnowledgeBase(organization_id=org.id, name="Policies", description=None)
    db_session.add(kb)
    db_session.flush()
    doc = Document(
        organization_id=org.id,
        knowledge_base_id=kb.id,
        title="Return policy",
        file_type="txt",
        file_size=0,
        status="queued",
    )
    db_session.add(doc)
    db_session.commit()

    text = "Our return policy allows returns within 30 days of purchase. " * 40
    result = tasks.ingest_document(db_session, doc.id, text.encode("utf-8"))
    assert result.ok is True
    assert result.detail["chunks"] > 0

    db_session.refresh(doc)
    assert doc.status == "ready"
    assert doc.chunk_count == result.detail["chunks"]


def test_ingest_document_records_failure_on_empty(db_session, org_factory):
    org = org_factory()
    from app.models.knowledge import Document, KnowledgeBase

    kb = KnowledgeBase(organization_id=org.id, name="KB", description=None)
    db_session.add(kb)
    db_session.flush()
    doc = Document(
        organization_id=org.id,
        knowledge_base_id=kb.id,
        title="Empty",
        file_type="txt",
        file_size=0,
        status="queued",
    )
    db_session.add(doc)
    db_session.commit()

    result = tasks.ingest_document(db_session, doc.id, b"   \n  ")
    assert result.ok is False
    db_session.refresh(doc)
    assert doc.status == "failed"
    assert doc.error_message


def test_finalize_call_summary_from_transcript(db_session, org_factory):
    org = org_factory()
    from app.models.call import Call, Transcript

    call = Call(
        organization_id=org.id,
        direction="inbound",
        phone_number="+1-800-555-0100",
        caller_id="+1-555-0199",
        status="in_progress",
        duration_seconds=90,
    )
    db_session.add(call)
    db_session.flush()
    db_session.add_all(
        [
            Transcript(call_id=call.id, speaker="agent", text="Hello", start_timestamp_ms=0, end_timestamp_ms=1000),
            Transcript(
                call_id=call.id,
                speaker="caller",
                text="I want to know about my order status please",
                start_timestamp_ms=1200,
                end_timestamp_ms=4000,
            ),
        ]
    )
    db_session.commit()

    result = tasks.finalize_call_summary(db_session, call.id)
    assert result.ok is True
    assert "order status" in result.detail["title"]
    db_session.refresh(call)
    assert call.status == "completed"
    assert call.summary
    assert call.estimated_cost > 0


def test_inline_runner_is_the_default():
    runner = InlineRunner()
    assert runner.name == "inline"

"""Tests for call orchestration: policy gates, inbound workflow, manual outbound (M3)."""
from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.models.agent import Agent
from app.models.contact import Contact, SuppressionEntry
from app.models.telephony import PhoneConnection
from app.services.calls.policy import (
    R_CONCURRENCY,
    R_DUPLICATE_CALL,
    R_LINE_UNVERIFIED,
    R_SUPPRESSED,
    PolicyEngine,
    within_calling_hours,
)
from app.services.telephony import factory
from app.services.telephony.mock_adapter import MockTelephonyAdapter

DID = "+1-800-555-0142"


@pytest.fixture(autouse=True)
def wide_calling_window(monkeypatch):
    """Calling-hours is tested directly; keep endpoint tests deterministic."""
    monkeypatch.setattr(settings, "DEFAULT_CALLING_HOURS_START", "00:00", raising=False)
    monkeypatch.setattr(settings, "DEFAULT_CALLING_HOURS_END", "23:59", raising=False)


@pytest.fixture(autouse=True)
def mock_provider():
    factory.set_adapter(MockTelephonyAdapter())
    yield
    factory.set_adapter(None)


@pytest.fixture()
def org(client):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "orch-owner@example.com",
            "full_name": "Orchestration Owner",
            "password": "Password123!",
            "organization_name": "Orchestration Co",
        },
    ).json()
    return reg


@pytest.fixture()
def headers(org):
    return {"Authorization": f"Bearer {org['access_token']}"}


@pytest.fixture()
def agent(db_session, org):
    a = Agent(
        organization_id=org["organization_id"],
        name="Support Agent",
        greeting="Hello, how can I help?",
        system_prompt="You are a helpful support agent.",
        direction="both",
        is_active=True,
        human_transfer_number="+1-800-HUMAN",
    )
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    return a


@pytest.fixture()
def connection(db_session, org, agent):
    c = PhoneConnection(
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
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


# --------------------------------------------------------------------------- #
# Pure policy helpers
# --------------------------------------------------------------------------- #
def test_within_calling_hours_inside_and_outside():
    noon = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    assert within_calling_hours("09:00", "20:00", noon, "UTC") is True

    late = datetime(2026, 5, 1, 22, 30, tzinfo=timezone.utc)
    assert within_calling_hours("09:00", "20:00", late, "UTC") is False


def test_within_calling_hours_overnight_window():
    one_am = datetime(2026, 5, 1, 1, 0, tzinfo=timezone.utc)
    assert within_calling_hours("22:00", "06:00", one_am, "UTC") is True
    midday = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    assert within_calling_hours("22:00", "06:00", midday, "UTC") is False


def test_policy_blocks_unverified_line(db_session, org, agent):
    unverified = PhoneConnection(
        organization_id=org["organization_id"],
        friendly_name="Unverified",
        phone_number="+1-800-555-0001",
        connection_type="gsm_gateway",
        is_verified=False,
        outbound_enabled=True,
    )
    db_session.add(unverified)
    db_session.commit()

    from app.models.tenant import Organization

    organization = db_session.query(Organization).filter(Organization.id == org["organization_id"]).first()
    decision = PolicyEngine(db_session).evaluate_outbound(organization, unverified, agent, "+1-555-0002")
    assert decision.allowed is False
    assert R_LINE_UNVERIFIED in decision.codes


def test_policy_blocks_suppressed_number(db_session, org, agent, connection):
    from app.models.tenant import Organization

    db_session.add(
        SuppressionEntry(
            organization_id=org["organization_id"],
            phone_number="+1-555-7777",
            reason="user_opt_out",
        )
    )
    db_session.commit()

    organization = db_session.query(Organization).filter(Organization.id == org["organization_id"]).first()
    decision = PolicyEngine(db_session).evaluate_outbound(
        organization, connection, agent, "+1-555-7777"
    )
    assert decision.allowed is False
    assert R_SUPPRESSED in decision.codes


# --------------------------------------------------------------------------- #
# Inbound webhook
# --------------------------------------------------------------------------- #
def test_inbound_unknown_number_is_rejected_not_dropped(client):
    resp = client.post(
        "/api/v1/telephony/inbound",
        json={"call_id": "c-unknown", "from_number": "+1-555-0100", "to_number": "+1-999-000-0000"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["action"] == "rejected"


def test_inbound_answers_and_bridges(client, connection):
    resp = client.post(
        "/api/v1/telephony/inbound",
        json={"call_id": "c-in-1", "from_number": "+1-555-0199", "to_number": DID},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["action"] == "answered"
    assert body["audio_bridge_uri"].startswith("ws://")
    assert body["status"] == "in_progress"
    assert body["organization_id"] == connection.organization_id

    detail = client.get(
        f"/api/v1/calls/{body['call_id']}",
        headers={"Authorization": f"Bearer {_token_for(client, 'orch-owner@example.com')}"},
    )
    assert detail.status_code == 200
    event_types = [e["event_type"] for e in detail.json()["events"]]
    assert "call_received" in event_types
    assert "call_answered" in event_types
    assert "audio_bridged" in event_types


def test_inbound_falls_back_to_human_when_agent_disabled(client, db_session, connection, agent):
    agent.is_active = False
    db_session.commit()

    resp = client.post(
        "/api/v1/telephony/inbound",
        json={"call_id": "c-in-2", "from_number": "+1-555-0199", "to_number": DID},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["action"] == "fallback"
    assert body["outcome"] == "human_transferred"


def test_inbound_rejects_when_no_fallback_available(client, db_session, connection, agent):
    agent.is_active = False
    agent.human_transfer_number = None
    db_session.commit()

    resp = client.post(
        "/api/v1/telephony/inbound",
        json={"call_id": "c-in-3", "from_number": "+1-555-0199", "to_number": DID},
    )
    body = resp.json()
    assert body["action"] == "rejected"
    assert body["status"] == "failed"
    # Honest reason, not a silent drop.
    assert body["policy"]["violations"][0]["code"]


# --------------------------------------------------------------------------- #
# Manual outbound
# --------------------------------------------------------------------------- #
def test_outbound_requires_confirmation(client, headers, connection, agent):
    resp = client.post(
        "/api/v1/calls/outbound",
        headers=headers,
        json={"to_number": "+1-555-0200", "connection_id": connection.id, "agent_id": agent.id},
    )
    assert resp.status_code == 409


def test_outbound_success_initiates(client, headers, connection, agent):
    resp = client.post(
        "/api/v1/calls/outbound",
        headers=headers,
        json={
            "to_number": "+1-555-0201",
            "connection_id": connection.id,
            "agent_id": agent.id,
            "reason": "Follow-up",
            "confirmed": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["action"] == "initiated"
    assert body["status"] in ("ringing", "queued")


def test_outbound_blocked_by_suppression(client, headers, db_session, org, connection, agent):
    db_session.add(
        SuppressionEntry(
            organization_id=org["organization_id"],
            phone_number="+1-555-0300",
            reason="user_opt_out",
        )
    )
    db_session.commit()

    resp = client.post(
        "/api/v1/calls/outbound",
        headers=headers,
        json={
            "to_number": "+1-555-0300",
            "connection_id": connection.id,
            "agent_id": agent.id,
            "confirmed": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["action"] == "blocked"
    assert R_SUPPRESSED in [v["code"] for v in body["policy"]["violations"]]


def test_outbound_records_carrier_failure_honestly(client, headers, connection, agent):
    resp = client.post(
        "/api/v1/calls/outbound",
        headers=headers,
        json={
            "to_number": "+1-555-0400",
            "connection_id": connection.id,
            "agent_id": agent.id,
            "confirmed": True,
            "metadata": {"simulate": "unreachable"},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["action"] == "failed"
    assert body["status"] == "failed"
    assert body["error"]["error"] == "destination_unreachable"


def test_outbound_blocks_duplicate_concurrent_call(client, headers, connection, agent):
    first = client.post(
        "/api/v1/calls/outbound",
        headers=headers,
        json={
            "to_number": "+1-555-0500",
            "connection_id": connection.id,
            "agent_id": agent.id,
            "confirmed": True,
        },
    )
    assert first.json()["action"] == "initiated"

    second = client.post(
        "/api/v1/calls/outbound",
        headers=headers,
        json={
            "to_number": "+1-555-0500",
            "connection_id": connection.id,
            "agent_id": agent.id,
            "confirmed": True,
        },
    )
    assert second.json()["action"] == "blocked"
    assert R_DUPLICATE_CALL in [v["code"] for v in second.json()["policy"]["violations"]]


# --------------------------------------------------------------------------- #
def _token_for(client, email: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    return resp.json()["access_token"]

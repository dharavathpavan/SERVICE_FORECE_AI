"""Tests for the live call WebSocket stream (M4)."""
import pytest

from app.models.agent import Agent
from app.models.telephony import PhoneConnection
from app.services.calls.events import EventHub
from app.services.telephony import factory
from app.services.telephony.mock_adapter import MockTelephonyAdapter

DID = "+1-800-555-0177"


@pytest.fixture(autouse=True)
def mock_provider():
    factory.set_adapter(MockTelephonyAdapter())
    yield
    factory.set_adapter(None)


@pytest.fixture()
def org(client):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": "ws-owner@example.com",
            "full_name": "WS Owner",
            "password": "Password123!",
            "organization_name": "Realtime Co",
        },
    ).json()


@pytest.fixture()
def line(db_session, org):
    agent = Agent(
        organization_id=org["organization_id"],
        name="Realtime Agent",
        greeting="Hi",
        system_prompt="Be helpful.",
        direction="both",
        is_active=True,
    )
    db_session.add(agent)
    db_session.flush()
    conn = PhoneConnection(
        organization_id=org["organization_id"],
        friendly_name="Realtime line",
        phone_number=DID,
        connection_type="gsm_gateway",
        is_verified=True,
        inbound_enabled=True,
        outbound_enabled=True,
        assigned_agent_id=agent.id,
    )
    db_session.add(conn)
    db_session.commit()
    db_session.refresh(conn)
    return conn


def _start_inbound(client) -> str:
    resp = client.post(
        "/api/v1/telephony/inbound",
        json={"call_id": "ws-call-1", "from_number": "+1-555-0199", "to_number": DID},
    )
    assert resp.status_code == 200, resp.text
    call_id = resp.json()["call_id"]
    assert call_id
    return call_id


def test_websocket_replays_and_streams_events(client, org, line):
    call_id = _start_inbound(client)
    token = org["access_token"]

    with client.websocket_connect(f"/api/v1/ws/calls/{call_id}?token={token}") as ws:
        seen = []
        for _ in range(3):
            seen.append(ws.receive_json())
        types = [e["event_type"] for e in seen]
        assert "call_received" in types
        assert "call_answered" in types
        assert all(e["call_id"] == call_id for e in seen)


def test_websocket_rejects_missing_token(client, org, line):
    call_id = _start_inbound(client)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/v1/ws/calls/{call_id}") as ws:
            ws.receive_json()


def test_event_hub_fanout_and_history():
    hub = EventHub()
    hub.publish("c1", {"event_type": "call_received"})
    hub.publish("c1", {"event_type": "call_answered"})
    history = hub.history("c1")
    assert [e["event_type"] for e in history] == ["call_received", "call_answered"]
    assert all("ts" in e for e in history)

    hub.clear("c1")
    assert hub.history("c1") == []

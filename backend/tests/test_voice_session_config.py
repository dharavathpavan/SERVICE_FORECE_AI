"""The live voice session must speak with the agent configured on the call.

``build_voice_config`` is the single place that maps an agent's stored prompt,
greeting, voice, language and enabled tools onto a provider session, and the
audio-bridge socket is exercised end to end so a regression in the wiring (not
just in the mapper) is caught.
"""
import pytest

from app.models.agent import Agent, AgentTool
from app.models.call import Call, Transcript
from app.models.telephony import PhoneConnection
from app.services.telephony import factory
from app.services.telephony.mock_adapter import MockTelephonyAdapter
from app.services.voice.session_config import build_voice_config

DID = "+1-800-555-0155"

GREETING = "Hi, this is Dana from the billing team."
PROMPT = "Handle billing questions and confirm the last invoice."


@pytest.fixture(autouse=True)
def mock_telephony():
    factory.set_adapter(MockTelephonyAdapter())
    yield
    factory.set_adapter(None)


@pytest.fixture()
def org(client):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": "voice-owner@example.com",
            "full_name": "Voice Owner",
            "password": "Password123!",
            "organization_name": "Voice Co",
        },
    ).json()


@pytest.fixture()
def agent(db_session, org):
    agent = Agent(
        organization_id=org["organization_id"],
        name="Billing Agent",
        greeting=GREETING,
        system_prompt=PROMPT,
        voice="Aoede",
        language="en-GB",
        direction="both",
        is_active=True,
    )
    db_session.add(agent)
    db_session.flush()
    db_session.add(
        AgentTool(
            agent_id=agent.id,
            tool_name="get_order_status",
            is_enabled=True,
            config={"lookup": "orders"},
        )
    )
    db_session.add(AgentTool(agent_id=agent.id, tool_name="disabled_tool", is_enabled=False))
    db_session.commit()
    db_session.refresh(agent)
    return agent


def _call(db_session, org, agent_id, number="+1-555-0100") -> Call:
    call = Call(
        organization_id=org["organization_id"],
        agent_id=agent_id,
        direction="outbound",
        phone_number=number,
        status="ringing",
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    return call


def test_config_is_taken_from_the_agent(db_session, org, agent):
    call = _call(db_session, org, agent.id)

    config = build_voice_config(db_session, call)

    assert config.call_id == call.id
    assert config.agent_name == "Billing Agent"
    assert config.system_prompt == PROMPT
    assert config.greeting == GREETING
    assert config.voice == "Aoede"
    assert config.language == "en-GB"
    assert config.context["phone_number"] == "+1-555-0100"


def test_config_exposes_only_enabled_tools(db_session, org, agent):
    call = _call(db_session, org, agent.id)

    config = build_voice_config(db_session, call)

    assert [tool["name"] for tool in config.tools] == ["get_order_status"]
    assert config.tools[0]["config"] == {"lookup": "orders"}


def test_config_falls_back_when_no_agent_is_bound(db_session, org):
    call = _call(db_session, org, agent_id=None)

    config = build_voice_config(db_session, call)

    assert config.agent_name == "ServiceForce Agent"
    assert config.tools == []
    # The bridge can still start, but nothing claims to be a configured agent.
    assert config.system_prompt
    assert config.greeting


def test_config_ignores_an_agent_from_another_organization(db_session, org, agent, client):
    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-owner@example.com",
            "full_name": "Other Owner",
            "password": "Password123!",
            "organization_name": "Other Co",
        },
    ).json()
    call = _call(db_session, other, agent.id)  # agent belongs to `org`

    config = build_voice_config(db_session, call)

    assert config.agent_name == "ServiceForce Agent"
    assert config.system_prompt != PROMPT


def test_audio_bridge_speaks_the_agent_greeting_and_records_the_call(
    client, db_session, org, agent
):
    connection = PhoneConnection(
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
    db_session.add(connection)
    db_session.commit()

    inbound = client.post(
        "/api/v1/telephony/inbound",
        json={"call_id": "voice-bridge-1", "from_number": "+1-555-0199", "to_number": DID},
    )
    assert inbound.status_code == 200, inbound.text
    call_id = inbound.json()["call_id"]
    assert inbound.json()["action"] == "answered"

    transcripts = []
    with client.websocket_connect(
        f"/api/v1/voice/stream?call_id={call_id}&token={org['access_token']}"
    ) as ws:
        for _ in range(7):
            message = ws.receive_json()
            if message.get("type") == "transcript":
                transcripts.append(message)

    spoken = [t["text"] for t in transcripts]
    # The agent introduced itself with the greeting configured on the agent.
    assert GREETING in spoken

    rows = db_session.query(Transcript).filter(Transcript.call_id == call_id).all()
    recorded = {row.text for row in rows}
    assert GREETING in recorded
    assert "I'd like to check my order status." in recorded
    assert all(row.speaker in {"agent", "caller", "system"} for row in rows)

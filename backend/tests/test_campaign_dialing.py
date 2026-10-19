"""Campaigns must actually dial, and must refuse numbers honestly.

Starting a campaign runs one dialer pass through the real policy engine, so these
tests assert on the calls that really exist afterwards - not on a status string.
"""
import pytest

from app.core.config import settings
from app.models.agent import Agent
from app.models.call import Call
from app.models.campaign import CampaignContact
from app.models.telephony import PhoneConnection
from app.services.telephony import factory
from app.services.telephony.mock_adapter import MockTelephonyAdapter

DID = "+1-800-555-0133"


@pytest.fixture(autouse=True)
def wide_calling_window(monkeypatch):
    """Calling hours are asserted elsewhere; keep these tests time-independent."""
    monkeypatch.setattr(settings, "DEFAULT_CALLING_HOURS_START", "00:00", raising=False)
    monkeypatch.setattr(settings, "DEFAULT_CALLING_HOURS_END", "23:59", raising=False)


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
            "email": "dialer-owner@example.com",
            "full_name": "Dialer Owner",
            "password": "Password123!",
            "organization_name": "Dialer Co",
        },
    ).json()


@pytest.fixture()
def headers(org):
    return {"Authorization": f"Bearer {org['access_token']}"}


@pytest.fixture()
def agent(db_session, org):
    agent = Agent(
        organization_id=org["organization_id"],
        name="Reminder Agent",
        greeting="Hello, this is a reminder about your appointment.",
        system_prompt="Confirm the appointment.",
        direction="outbound",
        is_active=True,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture()
def connection(db_session, org, agent):
    connection = PhoneConnection(
        organization_id=org["organization_id"],
        friendly_name="Outbound line",
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
    db_session.refresh(connection)
    return connection


def _contact(client, headers, number: str) -> str:
    resp = client.post(
        "/api/v1/contacts",
        headers=headers,
        json={"phone_number": number, "first_name": "Test", "consent_source": "web_form"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _campaign(client, headers, agent, connection, contact_ids, **overrides) -> dict:
    payload = {
        "name": "Reminder run",
        "agent_id": agent.id,
        "caller_connection_id": connection.id,
        "contact_ids": contact_ids,
        "allowed_start_hour": "00:00",
        "allowed_end_hour": "23:59",
        "concurrency_limit": 5,
    }
    payload.update(overrides)
    resp = client.post("/api/v1/campaigns", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_start_campaign_places_real_calls(client, db_session, headers, agent, connection):
    contact_ids = [_contact(client, headers, "+1-555-3001"), _contact(client, headers, "+1-555-3002")]
    campaign = _campaign(client, headers, agent, connection, contact_ids)
    assert campaign["status"] == "draft"

    started = client.post(f"/api/v1/campaigns/{campaign['id']}/start", headers=headers)
    assert started.status_code == 200, started.text
    body = started.json()
    assert body["status"] == "running"
    assert body["dialed"] == 2
    assert body["blocked"] == 0

    calls = db_session.query(Call).filter(Call.campaign_id == campaign["id"]).all()
    assert len(calls) == 2
    assert {c.phone_number for c in calls} == {"+1-555-3001", "+1-555-3002"}
    assert {c.direction for c in calls} == {"outbound"}
    assert {c.agent_id for c in calls} == {agent.id}

    links = (
        db_session.query(CampaignContact)
        .filter(CampaignContact.campaign_id == campaign["id"])
        .all()
    )
    assert {link.status for link in links} == {"calling"}
    assert all(link.attempts_count == 1 for link in links)


def test_second_sweep_does_not_redial_contacts(client, db_session, headers, agent, connection):
    contact_ids = [_contact(client, headers, "+1-555-3003")]
    campaign = _campaign(client, headers, agent, connection, contact_ids)
    client.post(f"/api/v1/campaigns/{campaign['id']}/start", headers=headers)

    again = client.post(f"/api/v1/campaigns/{campaign['id']}/sweep", headers=headers)
    assert again.status_code == 200
    assert again.json()["dialed"] == 0
    assert db_session.query(Call).filter(Call.campaign_id == campaign["id"]).count() == 1


def test_sweep_refuses_a_campaign_that_is_not_running(client, headers, agent, connection):
    contact_ids = [_contact(client, headers, "+1-555-3005")]
    campaign = _campaign(client, headers, agent, connection, contact_ids)

    resp = client.post(f"/api/v1/campaigns/{campaign['id']}/sweep", headers=headers)
    assert resp.status_code == 409
    assert "running" in resp.json()["detail"]


def test_dry_run_names_the_numbers_policy_would_refuse(client, headers, agent, connection):
    number = "+1-555-3007"
    contact_ids = [_contact(client, headers, number)]
    campaign = _campaign(client, headers, agent, connection, contact_ids)

    # Suppress *after* the campaign was built, so the contact is still pending.
    client.post(
        "/api/v1/contacts/suppress",
        headers=headers,
        json={"phone_number": number, "reason": "customer_request"},
    )

    dry = client.post(f"/api/v1/campaigns/{campaign['id']}/dry-run", headers=headers)
    assert dry.status_code == 200
    body = dry.json()
    assert body["pending_contacts"] == 1
    assert body["would_dial"] == 0
    assert body["would_block"] == 1
    assert body["blocked"][0]["phone_number"] == number
    assert "contact_suppressed" in body["blocked"][0]["reasons"]


def test_start_records_a_refused_contact_instead_of_dialing_it(
    client, db_session, headers, agent, connection
):
    number = "+1-555-3009"
    contact_ids = [_contact(client, headers, number)]
    campaign = _campaign(client, headers, agent, connection, contact_ids)
    client.post(
        "/api/v1/contacts/suppress",
        headers=headers,
        json={"phone_number": number, "reason": "customer_request"},
    )

    started = client.post(f"/api/v1/campaigns/{campaign['id']}/start", headers=headers)
    assert started.status_code == 200
    body = started.json()
    assert body["dialed"] == 0
    assert body["blocked"] == 1

    # Nothing was dialled, but the refusal is on record with its reason rather
    # than silently dropped.
    calls = db_session.query(Call).filter(Call.campaign_id == campaign["id"]).all()
    assert len(calls) == 1
    assert calls[0].status == "failed"
    assert "contact_suppressed" in (calls[0].failure_reason or "")
    assert calls[0].end_time is not None

    link = (
        db_session.query(CampaignContact)
        .filter(CampaignContact.campaign_id == campaign["id"])
        .first()
    )
    assert link.status == "opted_out"


def test_a_just_dialled_call_does_not_claim_a_resolved_outcome(
    client, db_session, headers, agent, connection
):
    """A ringing call has no outcome, and analytics must not count it as resolved."""
    contact_ids = [_contact(client, headers, "+1-555-3011")]
    campaign = _campaign(client, headers, agent, connection, contact_ids)
    client.post(f"/api/v1/campaigns/{campaign['id']}/start", headers=headers)

    call = db_session.query(Call).filter(Call.campaign_id == campaign["id"]).one()
    assert call.status == "ringing"
    assert call.outcome is None

    stats = client.get("/api/v1/analytics/summary?days=30", headers=headers).json()
    assert stats["ai_resolved_calls"] == 0

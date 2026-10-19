"""Tests for gateway/line health (M2): no fake 'online', real probe outcomes."""
import pytest

from app.services.telephony import factory
from app.services.telephony.adapter import TelephonyAdapter
from app.services.telephony.mock_adapter import MockTelephonyAdapter
from app.services.telephony.types import (
    CallSnapshot,
    Capability,
    CapabilityReport,
    ConnectivityResult,
    InboundEvent,
    LineStatus,
    NotSupportedError,
)


class _OfflineAdapter(TelephonyAdapter):
    """Adapter whose gateway is never reachable, for honest-failure tests."""

    provider_name = "offline-stub"

    def capabilities(self) -> CapabilityReport:
        return CapabilityReport(provider=self.provider_name, discovery=Capability.SUPPORTED)

    def discover_devices(self):
        return []

    def get_line_status(self, line_id=None):
        raise NotSupportedError("offline")

    def verify_connectivity(self, device_id=None) -> ConnectivityResult:
        return ConnectivityResult(ok=False, message="Gateway offline (stub).")

    def parse_inbound_event(self, payload) -> InboundEvent:
        raise NotSupportedError("offline")

    def answer_call(self, call_id) -> CallSnapshot:
        raise NotSupportedError("offline")

    def reject_call(self, call_id, reason="call_rejected") -> CallSnapshot:
        raise NotSupportedError("offline")

    def initiate_call(self, to_number, from_number, call_id, line_id=None, metadata=None) -> CallSnapshot:
        raise NotSupportedError("offline")

    def get_call_state(self, call_id) -> CallSnapshot:
        raise NotSupportedError("offline")

    def hangup_call(self, call_id, cause="normal_clearing") -> CallSnapshot:
        raise NotSupportedError("offline")

    def transfer_call(self, call_id, target) -> CallSnapshot:
        raise NotSupportedError("offline")

    def bridge_audio(self, call_id) -> str:
        raise NotSupportedError("offline")


@pytest.fixture()
def auth_headers(client):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "gateway-owner@example.com",
            "full_name": "Gateway Owner",
            "password": "Password123!",
            "organization_name": "Gateway Test Co",
        },
    )
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _mock_provider():
    """Default every test here to the deterministic mock provider."""
    factory.set_adapter(MockTelephonyAdapter())
    yield
    factory.set_adapter(None)


def test_new_gateway_is_unverified_not_online(client, auth_headers):
    resp = client.post(
        "/api/v1/gateways",
        headers=auth_headers,
        json={"identifier": "gw-1", "sip_endpoint": "sip:192.168.1.100:5060"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "unverified"
    assert body["connected"] is False
    assert body["last_heartbeat"] is None


def test_verify_gateway_sets_online_after_real_probe(client, auth_headers):
    created = client.post(
        "/api/v1/gateways",
        headers=auth_headers,
        json={"identifier": "gw-verify", "sip_endpoint": "sip:10.0.0.5:5060"},
    ).json()

    verify = client.post(f"/api/v1/gateways/{created['id']}/verify", headers=auth_headers)
    assert verify.status_code == 200, verify.text
    body = verify.json()
    assert body["status"] == "online"
    assert body["connected"] is True
    assert body["probe"]["ok"] is True
    assert body["probe"]["latency_ms"] is not None
    assert body["probe"]["lines"][0]["usable"] is True


def test_verify_gateway_reports_offline_honestly(client, auth_headers):
    created = client.post(
        "/api/v1/gateways",
        headers=auth_headers,
        json={"identifier": "gw-down", "sip_endpoint": "sip:10.0.0.9:5060"},
    ).json()

    factory.set_adapter(_OfflineAdapter())
    verify = client.post(f"/api/v1/gateways/{created['id']}/verify", headers=auth_headers)
    assert verify.status_code == 200, verify.text
    body = verify.json()
    assert body["status"] == "offline"
    assert body["connected"] is False
    assert body["probe"]["ok"] is False
    assert "offline" in body["probe"]["message"].lower()


def test_duplicate_gateway_identifier_conflicts(client, auth_headers):
    payload = {"identifier": "gw-dup", "sip_endpoint": "sip:10.0.0.1:5060"}
    assert client.post("/api/v1/gateways", headers=auth_headers, json=payload).status_code == 201
    second = client.post("/api/v1/gateways", headers=auth_headers, json=payload)
    assert second.status_code == 409


def test_gateway_identifier_is_unique_per_tenant_not_globally(client, auth_headers):
    """Two tenants may both name their gateway the same thing."""
    payload = {"identifier": "yeastar-tg200", "sip_endpoint": "sip:10.0.0.9:5060"}
    first = client.post("/api/v1/gateways", headers=auth_headers, json=payload)
    assert first.status_code == 201

    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "second-tenant@example.com",
            "full_name": "Second Tenant",
            "password": "Password123!",
            "organization_name": "Second Tenant Co",
        },
    ).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}

    assert client.post("/api/v1/gateways", headers=other_headers, json=payload).status_code == 201
    # ... and neither tenant can see the other's gateway.
    listed = client.get("/api/v1/gateways", headers=other_headers).json()
    assert len(listed) == 1
    assert listed[0]["id"] != first.json()["id"]


def test_phone_connection_starts_unverified_then_verifies(client, auth_headers):
    created = client.post(
        "/api/v1/phone-connections",
        headers=auth_headers,
        json={
            "friendly_name": "Main line",
            "phone_number": "+1-800-555-0100",
            "connection_type": "gsm_gateway",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["is_verified"] is False
    assert body["health_status"] == "unverified"

    verified = client.post(
        f"/api/v1/phone-connections/{body['id']}/verify", headers=auth_headers
    )
    assert verified.status_code == 200, verified.text
    vbody = verified.json()
    assert vbody["verified"] is True
    assert vbody["status"] == "healthy"


def test_phone_connection_verification_fails_honestly_when_offline(client, auth_headers):
    created = client.post(
        "/api/v1/phone-connections",
        headers=auth_headers,
        json={
            "friendly_name": "Down line",
            "phone_number": "+1-800-555-0199",
            "connection_type": "gsm_gateway",
        },
    ).json()

    factory.set_adapter(_OfflineAdapter())
    verified = client.post(
        f"/api/v1/phone-connections/{created['id']}/verify", headers=auth_headers
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["verified"] is False


def test_gateway_lines_endpoint(client, auth_headers):
    created = client.post(
        "/api/v1/gateways",
        headers=auth_headers,
        json={"identifier": "gw-lines", "sip_endpoint": "sip:10.0.0.2:5060"},
    ).json()

    resp = client.get(f"/api/v1/gateways/{created['id']}/lines", headers=auth_headers)
    assert resp.status_code == 200
    lines = resp.json()["lines"]
    assert lines and lines[0]["state"] == "registered"
    assert lines[0]["usable"] is True


def test_capabilities_endpoint_is_explicit(client, auth_headers):
    resp = client.get("/api/v1/telephony/capabilities", headers=auth_headers)
    assert resp.status_code == 200
    caps = resp.json()["capabilities"]
    assert caps["inbound_calls"] == "supported"
    assert caps["recording"] == "unsupported"  # mock is honest about this


def test_telephony_health_endpoint(client, auth_headers):
    resp = client.get("/api/v1/telephony/health", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["reachable"] is True


def test_gateway_scoped_to_organization(client, auth_headers):
    """Gateways from one tenant must not be visible to another."""
    client.post(
        "/api/v1/gateways",
        headers=auth_headers,
        json={"identifier": "gw-tenant-a", "sip_endpoint": "sip:10.0.0.3:5060"},
    )
    other = client.post(
        "/api/v1/auth/register",
        json={
            "email": "other-org@example.com",
            "full_name": "Other Owner",
            "password": "Password123!",
            "organization_name": "Other Co",
        },
    ).json()
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    listing = client.get("/api/v1/gateways", headers=other_headers)
    assert listing.status_code == 200
    assert listing.json() == []

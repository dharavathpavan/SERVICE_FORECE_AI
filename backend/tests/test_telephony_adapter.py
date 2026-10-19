"""Tests for the telephony adapter layer (M1)."""
import httpx
import pytest

from app.services.telephony import factory
from app.services.telephony.asterisk_adapter import AsteriskAdapter
from app.services.telephony.mock_adapter import MockTelephonyAdapter
from app.services.telephony.types import (
    AudioBridgeError,
    BusyError,
    CallNotFoundError,
    CallState,
    Capability,
    GatewayOfflineError,
    LineState,
    NotSupportedError,
    NoAnswerError,
    TelephonyError,
    UnreachableError,
)


@pytest.fixture()
def adapter() -> MockTelephonyAdapter:
    a = MockTelephonyAdapter()
    a.reset()
    return a


# --------------------------------------------------------------------------- #
# Mock adapter
# --------------------------------------------------------------------------- #
def test_mock_capabilities_are_honest(adapter):
    caps = adapter.capabilities()
    assert caps.provider == "mock"
    assert caps.inbound_calls == Capability.SUPPORTED
    # Recording is deliberately not claimed by the simulator.
    assert caps.recording == Capability.UNSUPPORTED


def test_mock_connectivity_and_line_status(adapter):
    conn = adapter.verify_connectivity()
    assert conn.ok is True
    assert conn.latency_ms is not None

    lines = adapter.get_line_status()
    assert len(lines) == 1
    assert lines[0].state == LineState.REGISTERED
    assert lines[0].usable is True


def test_mock_discovery_marks_device_reachable(adapter):
    devices = adapter.discover_devices()
    assert len(devices) == 1
    assert devices[0].reachable is True
    assert devices[0].lines and devices[0].lines[0].registration_ok


def test_mock_inbound_parse_requires_call_id(adapter):
    event = adapter.parse_inbound_event(
        {"call_id": "c-1", "from_number": "+1-555-0000", "to_number": "+1-800-555-0100"}
    )
    assert event.call_id == "c-1"
    assert event.event_type == "call_received"

    with pytest.raises(TelephonyError):
        adapter.parse_inbound_event({"from_number": "+1-555-0000"})


def test_mock_answer_and_reject_lifecycle(adapter):
    adapter.simulate_inbound("c-answer")
    snap = adapter.answer_call("c-answer")
    assert snap.state == CallState.IN_PROGRESS
    assert snap.answered_at is not None

    adapter.simulate_inbound("c-reject")
    rejected = adapter.reject_call("c-reject")
    assert rejected.state == CallState.REJECTED

    with pytest.raises(TelephonyError):
        adapter.answer_call("c-reject")  # already terminal


def test_mock_outbound_success(adapter):
    snap = adapter.initiate_call("+1-555-0199", "+1-800-555-0100", "out-1")
    assert snap.state == CallState.RINGING
    assert snap.channel and snap.channel.startswith("PJSIP/mock-out-")

    ended = adapter.hangup_call("out-1")
    assert ended.state == CallState.COMPLETED


@pytest.mark.parametrize(
    "mode,exc",
    [
        ("busy", BusyError),
        ("no_answer", NoAnswerError),
        ("unreachable", UnreachableError),
    ],
)
def test_mock_outbound_failures_raise_typed_errors(adapter, mode, exc):
    with pytest.raises(exc) as err:
        adapter.initiate_call(
            "+1-555-0199", "+1-800-555-0100", f"fail-{mode}", metadata={"simulate": mode}
        )
    assert err.value.code == exc.code
    # The failed call is still recorded so the UI never shows a phantom success.
    assert adapter.get_call_state(f"fail-{mode}").state == CallState.FAILED


def test_mock_transfer_and_audio_bridge(adapter):
    adapter.simulate_inbound("c-xfer")
    adapter.answer_call("c-xfer")
    transferred = adapter.transfer_call("c-xfer", "+1-800-HUMAN")
    assert transferred.state == CallState.TRANSFERRED
    assert transferred.transfer_target == "+1-800-HUMAN"

    adapter.simulate_inbound("c-audio")
    uri = adapter.bridge_audio("c-audio")
    assert uri.startswith("ws://")
    assert "c-audio" in uri


def test_mock_unknown_call_raises_not_found(adapter):
    with pytest.raises(CallNotFoundError):
        adapter.get_call_state("does-not-exist")


def test_mock_health_is_non_throwing(adapter):
    health = adapter.health()
    assert health["provider"] == "mock"
    assert health["reachable"] is True
    assert "capabilities" in health


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #
def test_factory_builds_mock_by_default():
    built = factory.build_adapter("mock")
    assert isinstance(built, MockTelephonyAdapter)


def test_factory_maps_sip_gateway_to_asterisk():
    built = factory.build_adapter("sip_gateway")
    assert isinstance(built, AsteriskAdapter)
    built.close()


def test_factory_rejects_unknown_provider():
    with pytest.raises(factory.UnknownTelephonyProvider):
        factory.build_adapter("carrier-pigeon")


def test_factory_set_adapter_override():
    sentinel = MockTelephonyAdapter()
    factory.set_adapter(sentinel)
    try:
        assert factory.get_adapter() is sentinel
    finally:
        factory.set_adapter(None)


# --------------------------------------------------------------------------- #
# Asterisk adapter (no live PBX: httpx MockTransport)
# --------------------------------------------------------------------------- #
def _asterisk_with(handler) -> AsteriskAdapter:
    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://pbx.local:8088/ari",
        auth=("u", "p"),
        timeout=2.0,
    )
    return AsteriskAdapter(
        host="pbx.local",
        ari_port=8088,
        username="u",
        password="p",
        client=client,
    )


def test_asterisk_connectivity_reports_offline_on_transport_error():
    def handler(request):  # pragma: no cover - raises before returning
        raise httpx.ConnectError("connection refused", request=request)

    adapter = _asterisk_with(handler)
    result = adapter.verify_connectivity()
    assert result.ok is False
    assert "offline" in result.message.lower() or "unreachable" in result.message.lower()
    adapter.close()


def test_asterisk_connectivity_ok_against_mock_transport():
    def handler(request):
        assert request.url.path.endswith("/asterisk/info")
        return httpx.Response(200, json={"system": {"version": "20.5.0"}, "build": {}, "config": {}})

    adapter = _asterisk_with(handler)
    result = adapter.verify_connectivity()
    assert result.ok is True
    assert result.latency_ms is not None
    adapter.close()


def test_asterisk_line_status_from_endpoints():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {"resource": "gw-sim-1", "state": "online", "technology": "PJSIP"},
                {"resource": "gw-sim-2", "state": "offline", "technology": "PJSIP"},
            ],
        )

    adapter = _asterisk_with(handler)
    lines = adapter.get_line_status()
    assert len(lines) == 2
    assert lines[0].state == LineState.REGISTERED
    assert lines[0].usable is True
    assert lines[1].state == LineState.UNREGISTERED
    assert lines[1].usable is False
    adapter.close()


def test_asterisk_originate_maps_404_to_unreachable():
    def handler(request):
        if request.method == "POST" and request.url.path.endswith("/channels"):
            return httpx.Response(404, json={"message": "Endpoint not found"})
        return httpx.Response(200, json={})

    adapter = _asterisk_with(handler)
    with pytest.raises(UnreachableError):
        adapter.initiate_call("+1-555-0199", "+1-800-555-0100", "call-1", line_id="PJSIP/nope")
    adapter.close()


def test_asterisk_answer_raises_gateway_offline_on_transport_error():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    adapter = _asterisk_with(handler)
    with pytest.raises(GatewayOfflineError):
        adapter.answer_call("chan-1")
    adapter.close()


def test_asterisk_parse_inbound_stasis_start():
    adapter = AsteriskAdapter(host="x", client=httpx.Client(base_url="http://x:1/ari"))
    event = adapter.parse_inbound_event(
        {
            "type": "StasisStart",
            "channel": {
                "id": "chan-9",
                "name": "PJSIP/gw-sim-1-00000001",
                "caller": {"number": "+1-555-0199"},
                "dialplan": {"exten": "+18005550100", "context": "from-serviceforce"},
            },
        }
    )
    assert event.event_type == "call_received"
    assert event.call_id == "chan-9"
    assert event.from_number == "+1-555-0199"
    adapter.close()


def test_asterisk_audio_bridge_failure_is_typed():
    def handler(request):
        return httpx.Response(500, text="externalMedia unavailable")

    adapter = _asterisk_with(handler)
    with pytest.raises(AudioBridgeError):
        adapter.bridge_audio("chan-1")
    adapter.close()


def test_not_supported_error_is_a_telephony_error():
    assert issubclass(NotSupportedError, TelephonyError)

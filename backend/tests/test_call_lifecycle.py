def test_call_simulation_and_metrics(client):
    reg = client.post("/api/v1/auth/register", json={
        "email": "telephony-lead@callforce.com",
        "full_name": "Telephony Lead",
        "password": "Password123!",
        "organization_name": "Call Force Logistics"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Register Phone Connection
    conn_resp = client.post("/api/v1/phone-connections", headers=headers, json={
        "friendly_name": "Main Hotline",
        "phone_number": "+1-800-555-0199",
        "connection_type": "mock",
        "inbound_enabled": True,
        "outbound_enabled": True
    })
    assert conn_resp.status_code == 201

    # 2. Simulate Order Tracking Call
    sim_resp = client.post("/api/v1/calls/simulate", headers=headers, json={
        "scenario": "order_tracking",
        "caller_phone": "+1-555-0199",
        "direction": "inbound"
    })
    assert sim_resp.status_code == 200
    call_id = sim_resp.json()["call_id"]
    assert sim_resp.json()["outcome"] == "ai_resolved"

    # 3. Fetch Call Detail
    detail_resp = client.get(f"/api/v1/calls/{call_id}", headers=headers)
    assert detail_resp.status_code == 200
    call_data = detail_resp.json()
    assert call_data["id"] == call_id
    assert call_data["duration_seconds"] > 0
    assert len(call_data["events"]) > 0
    assert len(call_data["transcripts"]) > 0

    # 4. Verify Analytics Summary captures the call
    analytics_resp = client.get("/api/v1/analytics/summary", headers=headers)
    assert analytics_resp.status_code == 200
    stats = analytics_resp.json()
    assert stats["total_calls"] >= 1
    assert stats["ai_resolved_calls"] >= 1
    assert stats["total_minutes"] > 0

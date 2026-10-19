import pytest
from app.services.tools.ssrf_guard import validate_url_safety
from fastapi import HTTPException


def test_tool_registry_execution(client):
    # Register user
    reg = client.post("/api/v1/auth/register", json={
        "email": "doctor@telehealth.com",
        "full_name": "Dr. House",
        "password": "Password123!",
        "organization_name": "House Clinic"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List tools
    tools_resp = client.get("/api/v1/tools", headers=headers)
    assert tools_resp.status_code == 200
    tool_names = [t["name"] for t in tools_resp.json()]
    assert "lookup_customer" in tool_names
    assert "get_order_status" in tool_names
    assert "check_inventory" in tool_names
    assert "create_appointment" in tool_names
    assert "request_human_transfer" in tool_names

    # 2. Execute lookup_customer
    lookup_resp = client.post("/api/v1/tools/execute", headers=headers, json={
        "tool_name": "lookup_customer",
        "parameters": {"phone_number": "+1-555-0199"}
    })
    assert lookup_resp.status_code == 200
    data = lookup_resp.json()
    assert data["status"] == "success"
    assert data["data"]["found"] is True
    assert data["data"]["customer"]["name"] == "Jane Cooper"

    # 3. Execute get_order_status
    order_resp = client.post("/api/v1/tools/execute", headers=headers, json={
        "tool_name": "get_order_status",
        "parameters": {"order_id": "ORD-8921"}
    })
    assert order_resp.status_code == 200
    assert order_resp.json()["data"]["found"] is True
    assert order_resp.json()["data"]["order"]["carrier"] == "FedEx Priority"

    # 4. Execute check_inventory
    inv_resp = client.post("/api/v1/tools/execute", headers=headers, json={
        "tool_name": "check_inventory",
        "parameters": {"item_or_sku": "Monitor"}
    })
    assert inv_resp.status_code == 200
    assert inv_resp.json()["data"]["in_stock"] is True

    # 5. Execute create_appointment with audit log verification
    apt_resp = client.post("/api/v1/tools/execute", headers=headers, json={
        "tool_name": "create_appointment",
        "parameters": {
            "customer_name": "Alice Smith",
            "customer_phone": "+1-555-9988",
            "date": "2026-10-25",
            "time_slot": "10:00 AM",
            "service_type": "Pediatric Consultation"
        }
    })
    assert apt_resp.status_code == 200
    assert apt_resp.json()["data"]["status"] == "confirmed"
    assert "confirmation_code" in apt_resp.json()["data"]["appointment"]


def test_ssrf_guard_blocks_internal_and_metadata_ips():
    # 1. AWS / Cloud metadata endpoint
    with pytest.raises(HTTPException) as exc_info:
        validate_url_safety("http://169.254.169.254/latest/meta-data/")
    assert exc_info.value.status_code == 403
    assert "strictly prohibited" in exc_info.value.detail

    # 2. Localhost
    with pytest.raises(HTTPException) as exc_info:
        validate_url_safety("http://127.0.0.1:8080/admin")
    assert exc_info.value.status_code == 403

    # 3. Disallowed protocols
    with pytest.raises(HTTPException) as exc_info:
        validate_url_safety("file:///etc/passwd")
    assert exc_info.value.status_code == 400

def test_campaign_and_suppression_workflow(client):
    reg = client.post("/api/v1/auth/register", json={
        "email": "campaigns-mgr@outboundai.com",
        "full_name": "Outbound Director",
        "password": "Password123!",
        "organization_name": "Outbound AI Services"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create an Agent for campaign
    agent_resp = client.post("/api/v1/agents", headers=headers, json={
        "name": "Appointment Reminder Agent",
        "purpose": "Appointment Confirmation",
        "greeting": "Hello, this is an automated reminder regarding your upcoming appointment.",
        "system_prompt": "Confirm client appointment details politely.",
        "direction": "outbound"
    })
    agent_id = agent_resp.json()["id"]

    # 2. Create Contacts
    c1_resp = client.post("/api/v1/contacts", headers=headers, json={
        "phone_number": "+1-555-1111",
        "first_name": "Robert",
        "consent_source": "customer_portal"
    })
    assert c1_resp.status_code == 201
    c1_id = c1_resp.json()["id"]

    c2_resp = client.post("/api/v1/contacts", headers=headers, json={
        "phone_number": "+1-555-2222",
        "first_name": "OptedOut",
        "consent_source": "customer_portal"
    })
    c2_id = c2_resp.json()["id"]

    # 3. Suppress Contact 2 (Do Not Call)
    client.post("/api/v1/contacts/suppress", headers=headers, json={
        "phone_number": "+1-555-2222",
        "reason": "customer_opt_out_request"
    })

    # 4. Create Campaign with both contacts
    camp_resp = client.post("/api/v1/campaigns", headers=headers, json={
        "name": "Weekly Confirmation Campaign",
        "agent_id": agent_id,
        "contact_ids": [c1_id, c2_id],
        "allowed_start_hour": "00:00",
        "allowed_end_hour": "23:59",
    })
    assert camp_resp.status_code == 201
    camp_data = camp_resp.json()
    assert camp_data["status"] == "draft"  # Must never auto-start
    # Suppressed contact was excluded
    assert camp_data["total_contacts"] == 1
    camp_id = camp_data["id"]

    # 5. Dry Run
    dry_resp = client.post(f"/api/v1/campaigns/{camp_id}/dry-run", headers=headers)
    assert dry_resp.status_code == 200
    assert dry_resp.json()["can_activate"] is True

    # 6. Explicitly Start Campaign
    start_resp = client.post(f"/api/v1/campaigns/{camp_id}/start", headers=headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "running"

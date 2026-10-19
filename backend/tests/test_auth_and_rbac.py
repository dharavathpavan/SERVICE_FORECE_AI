import pytest
from app.models.tenant import OrgRole


def test_register_and_login_flow(client):
    # 1. Register a new user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "sarah@apexcare.com",
            "full_name": "Sarah Connor",
            "password": "SecretPassword123!",
            "organization_name": "Apex Care Telehealth"
        }
    )
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert "access_token" in data
    assert data["role"] == "owner"
    assert data["organization_name"] == "Apex Care Telehealth"
    token = data["access_token"]
    org_id = data["organization_id"]

    # 2. Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "sarah@apexcare.com",
            "password": "SecretPassword123!"
        }
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["access_token"] is not None

    # 3. Access current org
    headers = {"Authorization": f"Bearer {token}"}
    org_resp = client.get("/api/v1/organizations/current", headers=headers)
    assert org_resp.status_code == 200
    assert org_resp.json()["id"] == org_id
    assert org_resp.json()["name"] == "Apex Care Telehealth"


def test_cross_tenant_access_denial(client):
    # Tenant 1: Org A
    user1_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@org-a.com",
            "full_name": "Admin A",
            "password": "PasswordA123!",
            "organization_name": "Tenant Alpha"
        }
    )
    token_a = user1_resp.json()["access_token"]
    org_a_id = user1_resp.json()["organization_id"]

    # Tenant 2: Org B
    user2_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@org-b.com",
            "full_name": "Admin B",
            "password": "PasswordB123!",
            "organization_name": "Tenant Beta"
        }
    )
    token_b = user2_resp.json()["access_token"]
    org_b_id = user2_resp.json()["organization_id"]

    # User B attempts to access Org A by spoofing header X-Organization-Id
    headers_spoofed = {
        "Authorization": f"Bearer {token_b}",
        "X-Organization-Id": org_a_id
    }
    denied_resp = client.get("/api/v1/organizations/current", headers=headers_spoofed)
    assert denied_resp.status_code == 403
    assert "Access denied to requested organization" in denied_resp.json()["detail"]


def test_rbac_invitations(client):
    user_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "ceo@serviceforce.ai",
            "full_name": "CEO ServiceForce",
            "password": "StrongPassword!2026",
            "organization_name": "ServiceForce HQ"
        }
    )
    token = user_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Invite operator
    invite_resp = client.post(
        "/api/v1/organizations/invite",
        headers=headers,
        json={"email": "operator1@serviceforce.ai", "role": "operator"}
    )
    assert invite_resp.status_code == 201
    assert invite_resp.json()["email"] == "operator1@serviceforce.ai"
    assert invite_resp.json()["role"] == "operator"
    assert invite_resp.json()["status"] == "pending"

    # List invitations
    list_resp = client.get("/api/v1/organizations/invitations", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

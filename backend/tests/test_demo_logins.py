"""The demo logins are part of the product contract.

Anyone cloning the repo must be able to sign in immediately, and each account
must honour exactly the same RBAC gates as a real user of that role.
"""

from app.db.seed import DEMO_PASSWORD, DEMO_USERS, ensure_demo_users
from app.models.tenant import OrganizationMembership, User


def _login(client, email: str, password: str = DEMO_PASSWORD):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_every_demo_login_authenticates_with_its_documented_role(
    client, db_session, org_factory
):
    org = org_factory(name="Apex Care Healthcare")
    ensure_demo_users(db_session, org)
    db_session.commit()

    for email, full_name, role in DEMO_USERS:
        resp = _login(client, email)
        assert resp.status_code == 200, f"{email} could not sign in: {resp.text}"

        body = resp.json()
        assert body["role"] == role.value
        assert body["organization_id"] == org.id
        assert body["user"]["email"] == email
        assert body["user"]["full_name"] == full_name
        assert body["access_token"]


def test_demo_login_rejects_a_wrong_password(client, db_session, org_factory):
    org = org_factory()
    ensure_demo_users(db_session, org)
    db_session.commit()

    resp = _login(client, DEMO_USERS[0][0], password="not-the-demo-password")
    assert resp.status_code == 401


def test_ensuring_demo_logins_twice_changes_nothing(client, db_session, org_factory):
    org = org_factory()

    first_owner = ensure_demo_users(db_session, org)
    db_session.commit()
    second_owner = ensure_demo_users(db_session, org)
    db_session.commit()

    assert first_owner.id == second_owner.id
    assert db_session.query(User).count() == len(DEMO_USERS)
    assert db_session.query(OrganizationMembership).count() == len(DEMO_USERS)


def test_demo_logins_respect_the_same_rbac_gates_as_real_users(
    client, db_session, org_factory
):
    org = org_factory()
    ensure_demo_users(db_session, org)
    db_session.commit()

    tokens = {
        role.value: _login(client, email).json()["access_token"]
        for email, _, role in DEMO_USERS
    }

    # The audit trail is owner/admin only.
    for role in ("owner", "admin"):
        resp = client.get("/api/v1/audit-logs", headers=_auth(tokens[role]))
        assert resp.status_code == 200, f"{role} should read the audit trail"

    for role in ("manager", "operator"):
        resp = client.get("/api/v1/audit-logs", headers=_auth(tokens[role]))
        assert resp.status_code == 403, f"{role} must not read the audit trail"

    # Every role can still read the team roster.
    for role, token in tokens.items():
        resp = client.get("/api/v1/organizations/members", headers=_auth(token))
        assert resp.status_code == 200, role
        assert len(resp.json()) == len(DEMO_USERS)

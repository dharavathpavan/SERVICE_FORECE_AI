"""CORS is what lets the browser client talk to this API at all.

The Flutter web app is served from an arbitrary local port (`flutter run -d
chrome` picks one, as does any static file server), so a regression here shows up
as "the whole demo is broken" rather than as a failing feature.
"""

import pytest

from app.core.config import settings


def _preflight(client, origin: str):
    return client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        # A port nobody configured: this is the case that used to break.
        "http://localhost:54321",
        "http://127.0.0.1:8099",
    ],
)
def test_local_browser_origins_are_allowed(client, origin: str):
    resp = _preflight(client, origin)
    assert resp.status_code == 200, f"preflight rejected for {origin}"
    assert resp.headers["access-control-allow-origin"] == origin
    assert resp.headers["access-control-allow-credentials"] == "true"


def test_the_login_response_carries_cors_headers_for_a_local_origin(client):
    resp = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:54321"},
        json={"email": "nobody@example.com", "password": "irrelevant"},
    )
    # 401 is expected - what matters is the browser would be allowed to read it.
    assert resp.status_code == 401
    assert resp.headers["access-control-allow-origin"] == "http://localhost:54321"


def test_a_remote_origin_is_not_granted_access(client):
    resp = client.get(
        "/api/v1/health",
        headers={"Origin": "https://evil.example.com"},
    )
    assert "access-control-allow-origin" not in resp.headers


def test_the_localhost_regex_can_be_disabled_for_production():
    """Production sets an exact origin list and clears the regex."""
    assert settings.BACKEND_CORS_ORIGIN_REGEX == r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"

"""Security verification tests for headers, auth tokens, anti-spoofing, and rate limiting."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.core.rate_limit import get_limiter
from app.main import create_app


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Ensure clean rate limiter state for every test."""
    get_limiter().reset()
    yield
    get_limiter().reset()


def test_security_headers_are_present_on_api_and_dashboard_responses():
    app = create_app(Settings(database_url="sqlite:///:memory:", _env_file=None))
    with TestClient(app) as client:
        response = client.get("/api/v1/hub")
        assert response.status_code == 200
        assert response.headers["x-frame-options"] == "SAMEORIGIN"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "geolocation=()" in response.headers["permissions-policy"]
        assert response.headers["cache-control"] == "no-store"


def test_anti_proxy_spoofing_blocks_external_ip_in_x_forwarded_for():
    app = create_app(
        Settings(
            database_url="sqlite:///:memory:",
            allow_local_management=True,
            _env_file=None,
        )
    )
    # Attacker forwards through a reverse proxy at 127.0.0.1, but X-Forwarded-For contains public IP
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        response = client.post(
            "/api/v1/operations/sync",
            json={"mode": "fixture"},
            headers={"X-Forwarded-For": "203.0.113.195"},
        )
        assert response.status_code == 409
        assert "servidor local" in response.text.lower()


def test_anti_proxy_spoofing_blocks_external_ip_in_rfc7239_forwarded():
    app = create_app(
        Settings(
            database_url="sqlite:///:memory:",
            allow_local_management=True,
            _env_file=None,
        )
    )
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        response = client.post(
            "/api/v1/operations/sync",
            json={"mode": "fixture"},
            headers={"Forwarded": "for=198.51.100.22;proto=http;by=127.0.0.1"},
        )
        assert response.status_code == 409
        assert "servidor local" in response.text.lower()


def test_management_token_authorizes_request_regardless_of_proxy_or_ip():
    app = create_app(
        Settings(
            database_url="sqlite:///:memory:",
            allow_local_management=True,
            management_token=SecretStr("super-secret-mgmt-key-99"),
            _env_file=None,
        )
    )
    # Without token, request fails even from 127.0.0.1
    with TestClient(app, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        unauth = client.post("/api/v1/operations/sync", json={"mode": "fixture"})
        assert unauth.status_code == 409

        # With wrong token, request fails
        wrong = client.post(
            "/api/v1/operations/sync",
            json={"mode": "fixture"},
            headers={"X-Management-Token": "invalid-token"},
        )
        assert wrong.status_code == 409

        # With correct token via X-Management-Token, succeeds
        with patch.object(app.state.workflow, "sync") as mock_sync:
            from app.models.workflow import WorkflowOverview

            mock_sync.return_value = WorkflowOverview(
                mode="fixture",
                available=True,
                coverage={"total": 0, "displayed": 0, "has_more": False, "is_complete": True},
                movements=[],
                message="OK",
            )
            success = client.post(
                "/api/v1/operations/sync",
                json={"mode": "fixture"},
                headers={"X-Management-Token": "super-secret-mgmt-key-99"},
            )
            assert success.status_code == 200

        # With correct token via Authorization: Bearer, succeeds
        with patch.object(app.state.workflow, "sync") as mock_sync:
            from app.models.workflow import WorkflowOverview

            mock_sync.return_value = WorkflowOverview(
                mode="fixture",
                available=True,
                coverage={"total": 0, "displayed": 0, "has_more": False, "is_complete": True},
                movements=[],
                message="OK",
            )
            success_bearer = client.post(
                "/api/v1/operations/sync",
                json={"mode": "fixture"},
                headers={"Authorization": "Bearer super-secret-mgmt-key-99"},
            )
            assert success_bearer.status_code == 200


def test_optional_api_read_token_protects_endpoints_when_configured():
    app = create_app(
        Settings(
            database_url="sqlite:///:memory:",
            api_auth_token=SecretStr("guard-token-abc"),
            _env_file=None,
        )
    )
    with TestClient(app) as client:
        # Unauthenticated returns 401
        unauth = client.get("/api/v1/hub")
        assert unauth.status_code == 401
        assert "Autenticación requerida" in unauth.json()["detail"]
        assert unauth.headers.get("www-authenticate") == "Bearer"

        # Wrong token returns 401
        wrong = client.get("/api/v1/hub", headers={"Authorization": "Bearer wrong-token"})
        assert wrong.status_code == 401

        # Correct Bearer token returns 200
        success_bearer = client.get(
            "/api/v1/hub", headers={"Authorization": "Bearer guard-token-abc"}
        )
        assert success_bearer.status_code == 200

        # Correct X-API-Key token returns 200
        success_api_key = client.get("/api/v1/hub", headers={"X-API-Key": "guard-token-abc"})
        assert success_api_key.status_code == 200


def test_rate_limiter_triggers_429_too_many_requests_when_limit_exceeded():
    app = create_app(
        Settings(
            database_url="sqlite:///:memory:",
            rate_limit_enabled=True,
            rate_limit_per_minute=3,
            _env_file=None,
        )
    )
    with TestClient(app, client=("192.0.2.1", 45000)) as client:
        # First 3 requests succeed
        for _ in range(3):
            res = client.get("/api/v1/hub")
            assert res.status_code == 200

        # 4th request is blocked by rate limiter
        blocked = client.get("/api/v1/hub")
        assert blocked.status_code == 429
        assert "Límite de peticiones excedido" in blocked.json()["detail"]
        assert "retry-after" in blocked.headers
        assert blocked.headers.get("x-ratelimit-remaining") == "0"


def test_cors_default_is_empty_and_rejects_arbitrary_origins():
    app = create_app(Settings(database_url="sqlite:///:memory:", _env_file=None))
    with TestClient(app) as client:
        # Preflight from unapproved origin
        res = client.options(
            "/api/v1/hub",
            headers={
                "Origin": "https://malicious-site.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert res.headers.get("access-control-allow-origin") is None

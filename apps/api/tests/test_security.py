"""Security review follow-ups: throttling keys, headers, origin checks, local icons, CLI input."""

import io
import re
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.cli.create_user import main as create_user
from app.core.auth import RECEIPT_PATH, Role
from app.core.config import Settings
from app.dashboard.components import ICONS, icon
from tests.test_auth import PASSWORD, add_user, build_app, login, open_client


def test_failures_are_counted_per_address_and_email(tmp_path):
    app = build_app(tmp_path)
    with open_client(app, client=("10.0.0.9", 4000)) as client, patch("app.api.auth._failures", {}):
        for _ in range(10):
            assert login(client, "x@example.com", "wrong-password").status_code == 401
        assert login(client, "x@example.com", "wrong-password").status_code == 429
        # Another account from the same address is not locked out.
        assert login(client, "y@example.com", "wrong-password").status_code == 401
        # 20 failures for one email across addresses lock the email for a new address too.
        other = TestClient(app, client=("10.0.0.10", 4000))
        for _ in range(10):
            assert login(other, "x@example.com", "wrong-password").status_code == 401
        third = TestClient(app, client=("10.0.0.11", 4000))
        assert login(third, "x@example.com", "wrong-password").status_code == 429


def test_security_headers_and_csp_on_html_only(tmp_path):
    app = build_app(tmp_path)
    with open_client(app) as client:
        page = client.get("/login")
        assert page.headers["x-content-type-options"] == "nosniff"
        assert page.headers["referrer-policy"] == "same-origin"
        assert page.headers["x-frame-options"] == "DENY"
        assert "strict-transport-security" not in page.headers
        csp = page.headers["content-security-policy"]
        assert "content-security-policy-report-only" not in page.headers
        assert csp.startswith("default-src 'self'; script-src 'self' 'unsafe-eval' 'sha256-")
        assert "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
        assert client.get("/_dash-layout").headers["cache-control"] == "no-store"
        health = client.get("/health/live")
        assert "content-security-policy" not in health.headers
        assert health.headers["x-content-type-options"] == "nosniff"
        suite = re.search(r'src="(/_dash-component-suites/[^"]+)"', page.text).group(1)
        assert client.get(suite).headers["cache-control"] != "no-store"
    with open_client(build_app(tmp_path, session_https_only=True)) as client:
        hsts = client.get("/health/live").headers["strict-transport-security"]
        assert hsts == "max-age=31536000; includeSubDomains"


def test_session_cookie_is_secure_by_default(monkeypatch):
    monkeypatch.delenv("SESSION_HTTPS_ONLY", raising=False)
    settings = Settings(database_url="sqlite://", auth_required=False, _env_file=None)
    assert settings.session_https_only is True


def test_cross_origin_writes_are_rejected(tmp_path):
    app = build_app(tmp_path)
    with open_client(app) as client:
        add_user(app, "ana@example.com", Role.lectura)
        login(client, "ana@example.com")
        evil = client.post("/api/v1/auth/logout", headers={"Origin": "https://evil.example"})
        assert evil.status_code == 403
        assert evil.json() == {"detail": "Origen no permitido"}
        fetch = client.post("/_dash-update-component", headers={"Sec-Fetch-Site": "cross-site"})
        assert fetch.status_code == 403
        safe = client.get("/api/v1/auth/me", headers={"Origin": "https://evil.example"})
        assert safe.status_code == 200
        headers = {"Origin": "http://testserver", "Sec-Fetch-Site": "same-origin"}
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204


def test_icons_are_local_tabler_files(tmp_path):
    names: set[str] = set()
    for path in ICONS.parent.parent.glob("*.py"):
        text = path.read_text()
        names.update(re.findall(r'icon\("([a-z0-9-]+)"', text))
        names.update(re.findall(r'icon_name="([a-z0-9-]+)"', text))
        names.update(re.findall(r'"icon": "([a-z0-9-]+)"', text))
    assert names and all((ICONS / f"{name}.svg").is_file() for name in names)
    assert (ICONS / "LICENSE-tabler.txt").read_text().startswith("MIT License")
    mark = icon("search", 16)
    assert mark.className == "ui-icon" and mark.style["--icon"] == "url(/assets/icons/search.svg)"
    with pytest.raises(ValueError, match="no vendorizado"):
        icon("does-not-exist")
    with open_client(build_app(tmp_path)) as client:
        asset = client.get("/assets/icons/search.svg")
        assert asset.status_code == 200 and "svg" in asset.headers["content-type"]
        assert 'stroke="currentColor"' in asset.text


def test_receipt_path_tolerates_a_trailing_slash():
    assert RECEIPT_PATH.fullmatch("/api/v1/operations/m-1/receipt/")
    assert not RECEIPT_PATH.fullmatch("/api/v1/operations/m-1/receipt/extra")


def test_cli_rejects_invalid_email_and_name(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(f"{PASSWORD}\n"))
    args = ["--email", "not-an-email", "--role", "admin", "--password-stdin"]
    assert create_user(args) == 2
    assert "email" in capsys.readouterr().err
    monkeypatch.setattr("sys.stdin", io.StringIO(f"{PASSWORD}\n"))
    args = ["--email", "ok@example.com", "--role", "admin", "--name", "x" * 256, "--password-stdin"]
    assert create_user(args) == 2
    assert "full_name" in capsys.readouterr().err

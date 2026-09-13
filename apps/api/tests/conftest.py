"""Existing tests build Settings(_env_file=None) without a login; keep them in dev mode."""

import os

import pytest

os.environ.setdefault("AUTH_REQUIRED", "false")
# TestClient speaks plain http; a Secure cookie would never be sent back.
os.environ.setdefault("SESSION_HTTPS_ONLY", "false")


@pytest.fixture(autouse=True)
def local_development_mode(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.setenv("SESSION_HTTPS_ONLY", "false")

"""Request-scoped local management boundary; no browser flag grants authority."""

import secrets
from contextlib import contextmanager
from contextvars import ContextVar
from ipaddress import ip_address

from starlette.requests import Request

_local_management: ContextVar[bool] = ContextVar("econ_local_management", default=False)


def management_allowed() -> bool:
    return _local_management.get()


@contextmanager
def management_scope(allowed: bool):
    token = _local_management.set(allowed)
    try:
        yield
    finally:
        _local_management.reset(token)


def _extract_token(request: Request) -> str | None:
    token_header = request.headers.get("x-management-token")
    if token_header:
        return token_header.strip()
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None


def local_request(request: Request) -> bool:
    settings = getattr(getattr(request.app, "state", None), "settings", None)
    configured_token = (
        settings.management_token.get_secret_value()
        if settings and settings.management_token
        else None
    )

    client_token = _extract_token(request)
    if configured_token:
        return bool(client_token and secrets.compare_digest(client_token, configured_token))

    # Anti-proxy spoofing: if proxy headers indicate external client, deny loopback trust
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        origin_ip_str = forwarded_for.split(",")[0].strip()
        try:
            if not ip_address(origin_ip_str).is_loopback:
                return False
        except ValueError:
            return False

    if request.headers.get("forwarded"):
        forwarded_raw = request.headers.get("forwarded", "")
        for part in forwarded_raw.split(";"):
            part = part.strip()
            if part.lower().startswith("for="):
                for_ip = part[4:].strip().strip('"').strip("[]")
                try:
                    if not ip_address(for_ip).is_loopback:
                        return False
                except ValueError:
                    return False

    try:
        loopback = request.client is not None and ip_address(request.client.host).is_loopback
    except ValueError:
        return False
    hostname = request.url.hostname
    if not loopback or hostname not in {"localhost", "127.0.0.1", "::1"}:
        return False
    if request.headers.get("sec-fetch-site") == "cross-site":
        return False
    origin = request.headers.get("origin")
    return origin is None or origin == f"{request.url.scheme}://{request.url.netloc}"

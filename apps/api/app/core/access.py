"""Request-scoped management boundary; authority comes from the session role or local dev mode."""

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


def local_request(request: Request) -> bool:
    """Loopback, same-origin request: the only management authority when AUTH_REQUIRED=false."""
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

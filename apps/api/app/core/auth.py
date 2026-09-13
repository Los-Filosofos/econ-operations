"""Roles, permissions and the session identity behind every request.

Sessions are signed cookies (Starlette SessionMiddleware); the role is read from SQL on each
request, so deactivating a user or resetting a password ends their sessions immediately.
"""

import re
from collections.abc import Callable
from enum import StrEnum
from hashlib import sha256
from typing import Annotated
from urllib.parse import quote

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyCookie
from pwdlib import PasswordHash
from sqlmodel import Session
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.core.access import local_request
from app.core.config import Settings
from app.models.operations import Actor, ActorKind
from app.models.users import User

SESSION_COOKIE = "econ_session"
DASH_UPDATE_PATH = "/_dash-update-component"
# Served without a session: health, the login page and what Dash needs to render it.
PUBLIC_PATHS = (
    "/health/",
    "/login",
    "/api/v1/auth/login",
    "/assets/",
    "/_favicon.ico",
    "/_dash-component-suites/",
    "/_dash-layout",
    "/_dash-dependencies",
    DASH_UPDATE_PATH,
)
# Static paths never need the user loaded from SQL.
STATIC_PATHS = ("/health/", "/assets/", "/_favicon.ico", "/_dash-component-suites/")
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
RECEIPT_PATH = re.compile(r"/api/v1/operations/[^/]+/receipt/?")
# Operator exit from `unknown`; it changes local state only and never repeats a provider POST.
RESOLVE_PATH = re.compile(r"/api/v1/operations/[^/]+/resolve/?")
CROSS_ORIGIN_SITES = frozenset({"cross-site", "same-site"})


class Role(StrEnum):
    admin = "admin"
    gerencia_proyecto = "gerencia_proyecto"
    logistica = "logistica"
    mantenimiento = "mantenimiento"
    control_costos = "control_costos"
    lectura = "lectura"


class Permission(StrEnum):
    read = "read"
    manage_transfers = "manage_transfers"
    declare_reception = "declare_reception"
    manage_users = "manage_users"


PERMISSIONS: dict[Permission, frozenset[Role]] = {
    Permission.read: frozenset(Role),
    Permission.manage_transfers: frozenset({Role.logistica, Role.admin}),
    Permission.declare_reception: frozenset({Role.gerencia_proyecto, Role.logistica, Role.admin}),
    Permission.manage_users: frozenset({Role.admin}),
}
MANAGEMENT = (Permission.manage_transfers, Permission.declare_reception)

password_hasher = PasswordHash.recommended()


def can(role: str, permission: Permission) -> bool:
    return role in PERMISSIONS[permission]


def permissions_of(role: str) -> list[Permission]:
    return [permission for permission in Permission if can(role, permission)]


def _stamp(user: User) -> str:
    # Changing the password invalidates sessions issued before the change.
    return sha256(user.password_hash.encode()).hexdigest()[:16]


def start_session(request: Request, user: User) -> None:
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["stamp"] = _stamp(user)
    request.state.user = user


def end_session(request: Request) -> None:
    request.session.clear()
    request.state.user = None


def load_session_user(request: Request) -> User | None:
    """Active user for the session cookie, loaded once per request into request.state.user."""
    if hasattr(request.state, "user"):
        return request.state.user
    user = None
    user_id = request.session.get("user_id")
    if user_id is not None:
        with Session(request.app.state.engine) as db:
            user = db.get(User, user_id)
        if user is None or not user.is_active or _stamp(user) != request.session.get("stamp"):
            request.session.clear()
            user = None
    request.state.user = user
    return user


def session_user() -> User | None:
    """Current user inside a Dash callback; None when anonymous or outside a request."""
    from dash import get_app

    try:
        state = get_app().backend.request_adapter().context
    except RuntimeError:
        return None
    return getattr(state, "user", None)


def actor_from_user(user: User | None, *, kind: ActorKind) -> Actor | None:
    """Ledger actor for a real user or for an explicit process; never a fabricated identity.

    With a user the actor is always `session` (id, email and role come from the row read
    from SQL). Without a user, `session` yields None and `local_dev` / `cli_worker`
    yield an actor that carries no user at all.
    """
    if user is not None:
        return Actor(user_id=str(user.id), email=user.email, role=user.role, kind="session")
    if kind == "session":
        return None
    return Actor(kind=kind)


def request_actor(request: Request) -> Actor | None:
    """Who acts in this HTTP request: the session user, the loopback developer, or nobody."""
    user = load_session_user(request)
    if user is not None:
        return actor_from_user(user, kind="session")
    settings = getattr(request.app.state, "settings", None)
    if (
        settings is not None
        and not settings.auth_required
        and settings.allow_local_management
        and local_request(request)
    ):
        return actor_from_user(None, kind="local_dev")
    return None


def write_permission(request: Request) -> Permission:
    """Permission this request needs; Dash callbacks gate their own actions with session_user()."""
    path = request.url.path
    if request.method in SAFE_METHODS or path == DASH_UPDATE_PATH:
        return Permission.read
    if RECEIPT_PATH.fullmatch(path):
        return Permission.declare_reception
    if RESOLVE_PATH.fullmatch(path):
        return Permission.manage_transfers
    if path.startswith("/api/v1/operations"):
        return Permission.manage_transfers
    if path.startswith("/api/v1/users"):
        return Permission.manage_users
    return Permission.read


def management_granted(request: Request, user: User | None) -> bool:
    """Whether services.workflow may mutate during this request (see management_scope)."""
    if user is None:
        return False
    if request.method in SAFE_METHODS or request.url.path == DASH_UPDATE_PATH:
        return any(can(user.role, permission) for permission in MANAGEMENT)
    return can(user.role, write_permission(request))


def _unauthenticated(request: Request) -> Response:
    if request.url.path.startswith(("/api/", "/_dash-")):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": "Autenticación requerida"}
        )
    target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    return RedirectResponse(f"/login?next={quote(target, safe='')}", status_code=302)


def cross_origin(request: Request) -> bool:
    """A state-changing request from another origin, per Fetch metadata or the Origin header."""
    if request.method in SAFE_METHODS and request.url.path != DASH_UPDATE_PATH:
        return False
    if request.headers.get("sec-fetch-site", "").lower() in CROSS_ORIGIN_SITES:
        return True
    origin = request.headers.get("origin")
    return origin is not None and origin != f"{request.url.scheme}://{request.url.netloc}"


def authorize_request(request: Request, settings: Settings) -> Response | bool:
    """Reject the request or return the management authority for it."""
    path = request.url.path
    if cross_origin(request):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Origen no permitido"}
        )
    user = None if path.startswith(STATIC_PATHS) else load_session_user(request)
    if user is not None:
        if not can(user.role, write_permission(request)):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN, content={"detail": "Permiso insuficiente"}
            )
    elif settings.auth_required and not path.startswith(PUBLIC_PATHS):
        return _unauthenticated(request)
    local_dev = (
        not settings.auth_required and settings.allow_local_management and local_request(request)
    )
    return local_dev or management_granted(request, user)


session_cookie = APIKeyCookie(
    name=SESSION_COOKIE,
    auto_error=False,
    description="Cookie HttpOnly firmada que crea POST /api/v1/auth/login.",
)


def require(permission: Permission) -> Callable[..., User]:
    """FastAPI dependency: the active session user, who must hold the permission."""

    def dependency(
        request: Request, _cookie: Annotated[str | None, Security(session_cookie)]
    ) -> User:
        user = load_session_user(request)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticación requerida")
        if not can(user.role, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permiso insuficiente")
        return user

    return dependency

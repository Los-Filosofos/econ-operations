"""Session login over the signed cookie; failures never reveal whether an email exists."""

from threading import Lock
from time import monotonic

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlmodel import Session, select

from app.api.documentation import ErrorResponse
from app.core.auth import (
    Permission,
    end_session,
    load_session_user,
    password_hasher,
    permissions_of,
    start_session,
)
from app.models.users import User, UserRecord

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])

# Failures are counted per (address, email) so one address cannot lock out every user and one
# email cannot be brute-forced from many addresses; a broader per-email counter covers the latter.
MAX_FAILURES = 10
MAX_EMAIL_FAILURES = 20
FAILURE_WINDOW_SECONDS = 15 * 60
_failures: dict[str, list[float]] = {}
_failures_lock = Lock()


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class SessionRecord(UserRecord):
    permissions: list[Permission]


def _session_record(user: User) -> SessionRecord:
    record = UserRecord.model_validate(user)
    return SessionRecord(**record.model_dump(), permissions=permissions_of(user.role))


def _recent_failures(key: str) -> list[float]:
    cutoff = monotonic() - FAILURE_WINDOW_SECONDS
    recent = [moment for moment in _failures.get(key, []) if moment > cutoff]
    if recent:
        _failures[key] = recent
    else:
        _failures.pop(key, None)
    return recent


def _failure_keys(host: str, email: str) -> tuple[str, str]:
    return f"{host}|{email}", f"email:{email}"


def _throttled(host: str, email: str) -> bool:
    pair_key, email_key = _failure_keys(host, email)
    return (
        len(_recent_failures(pair_key)) >= MAX_FAILURES
        or len(_recent_failures(email_key)) >= MAX_EMAIL_FAILURES
    )


@router.post(
    "/login",
    summary="Iniciar sesión",
    description=(
        "Valida email y contraseña y crea la cookie de sesión HttpOnly. Un fallo devuelve 401 "
        "sin indicar si el email existe. Más de 10 fallos por IP y email (o 20 por email) en "
        "15 minutos devuelven 429."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Credenciales inválidas o usuario inactivo."},
        429: {"model": ErrorResponse, "description": "Demasiados intentos para esta cuenta."},
    },
)
def login(request: Request, credentials: LoginInput) -> SessionRecord:
    host = request.client.host if request.client else "unknown"
    email = credentials.email.lower()
    with _failures_lock:
        if _throttled(host, email):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Demasiados intentos; espera.")
    with Session(request.app.state.engine) as db:
        user = db.exec(select(User).where(User.email == email)).first()
        if user is not None and user.is_active:
            verified, updated_hash = password_hasher.verify_and_update(
                credentials.password, user.password_hash
            )
            if updated_hash:
                user.password_hash = updated_hash
                db.add(user)
                db.commit()
                db.refresh(user)
        else:
            # Hash anyway so timing does not distinguish unknown emails.
            password_hasher.hash(credentials.password)
            verified = False
    if not verified:
        with _failures_lock:
            for key in _failure_keys(host, email):
                _failures.setdefault(key, []).append(monotonic())
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    with _failures_lock:
        for key in _failure_keys(host, email):
            _failures.pop(key, None)
    start_session(request, user)
    return _session_record(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión",
    description="Elimina la cookie de sesión. Responde 204 aunque no hubiera sesión.",
)
def logout(request: Request) -> None:
    end_session(request)


@router.get(
    "/me",
    summary="Consultar la sesión actual",
    description="Devuelve el usuario activo de la cookie y sus permisos efectivos.",
    responses={401: {"model": ErrorResponse, "description": "No hay sesión válida."}},
)
def me(request: Request) -> SessionRecord:
    user = load_session_user(request)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticación requerida")
    return _session_record(user)

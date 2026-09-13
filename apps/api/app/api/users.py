"""User administration for the admin role; the last active admin cannot lock everyone out."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.api.documentation import ErrorResponse
from app.core.auth import PERMISSIONS, Permission, Role, password_hasher, require
from app.models.users import User, UserRecord

router = APIRouter(
    prefix="/api/v1/users",
    tags=["Usuarios"],
    dependencies=[Depends(require(Permission.manage_users))],
    responses={
        401: {"model": ErrorResponse, "description": "No hay sesión válida."},
        403: {"model": ErrorResponse, "description": "La sesión no tiene manage_users."},
    },
)

ROLE_DESCRIPTION = "Rol funcional: " + "; ".join(
    f"{role.value} → "
    + ", ".join(permission.value for permission, roles in PERMISSIONS.items() if role in roles)
    for role in Role
)
Password = Annotated[str, Field(min_length=12, max_length=1024)]


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: Role = Field(description=ROLE_DESCRIPTION)
    password: Password


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: Role | None = Field(default=None, description=ROLE_DESCRIPTION)
    is_active: bool | None = None
    password: Password | None = Field(
        default=None, description="Nueva contraseña; cierra las sesiones previas del usuario."
    )


def new_user(email: str, full_name: str, role: Role, password: str) -> User:
    return User(
        email=email.lower(),
        full_name=full_name,
        role=role,
        password_hash=password_hasher.hash(password),
        created_at=datetime.now(UTC),
    )


def _other_active_admins(db: Session, user_id: int) -> int:
    statement = select(func.count()).where(
        User.role == Role.admin, User.is_active.is_(True), User.id != user_id
    )
    return db.exec(statement).one()


@router.get("", summary="Listar usuarios", description="Devuelve todos los usuarios sin hashes.")
def list_users(request: Request) -> list[UserRecord]:
    with Session(request.app.state.engine) as db:
        users = db.exec(select(User).order_by(User.email)).all()
    return [UserRecord.model_validate(user) for user in users]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    description="Crea un usuario activo con rol y contraseña (mínimo 12 caracteres).",
    responses={409: {"model": ErrorResponse, "description": "El email ya existe."}},
)
def create_user(request: Request, data: UserCreate) -> UserRecord:
    user = new_user(data.email, data.full_name, data.role, data.password)
    with Session(request.app.state.engine) as db:
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, "El email ya existe.") from None
        db.refresh(user)
    return UserRecord.model_validate(user)


@router.patch(
    "/{user_id}",
    summary="Actualizar usuario",
    description=(
        "Cambia nombre, rol, estado o contraseña. Un administrador no puede desactivarse a sí "
        "mismo ni dejar el sistema sin administradores activos."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Usuario inexistente."},
        409: {"model": ErrorResponse, "description": "El cambio dejaría sin administrador."},
    },
)
def update_user(
    request: Request,
    user_id: Annotated[int, Path(description="ID devuelto por GET /api/v1/users.")],
    data: UserUpdate,
    actor: Annotated[User, Depends(require(Permission.manage_users))],
) -> UserRecord:
    with Session(request.app.state.engine) as db:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario inexistente.")
        loses_admin = (data.is_active is False) or (
            data.role is not None and data.role != Role.admin
        )
        if user.role == Role.admin and user.is_active and loses_admin:
            if user.id == actor.id and data.is_active is False:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "No puedes desactivar tu propia cuenta."
                )
            if _other_active_admins(db, user.id) == 0:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "Debe quedar al menos un administrador activo."
                )
        for field, value in data.model_dump(exclude_unset=True, exclude={"password"}).items():
            setattr(user, field, value)
        if data.password is not None:
            user.password_hash = password_hasher.hash(data.password)
        db.add(user)
        db.commit()
        db.refresh(user)
    return UserRecord.model_validate(user)

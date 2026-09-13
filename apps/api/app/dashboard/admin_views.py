"""User administration page. Every rule (unique email, last active admin, password length)
lives in app.api.users; the callbacks call those handlers so the browser cannot bypass them."""

from datetime import UTC
from types import SimpleNamespace

import dash_mantine_components as dmc
from dash import ALL, Input, Output, State, ctx, dcc, html, no_update
from fastapi import HTTPException
from pydantic import ValidationError
from sqlmodel import Session

from app.api.users import UserCreate, UserUpdate, create_user, list_users, update_user
from app.core.auth import Permission, Role, can, permissions_of
from app.dashboard.analytics import instant
from app.dashboard.auth_views import ROLE_LABELS, current_user, permission_note
from app.dashboard.components import (
    eyebrow,
    heading,
    hint,
    icon,
    notice,
    section,
    simple_table,
)
from app.models.users import User

ROLE_OPTIONS = [{"value": role.value, "label": ROLE_LABELS[role]} for role in Role]
# Wording of each permission for people who do not read the permission table in the ADR.
PERMISSION_LABELS = {
    Permission.read: "Consultar el hub",
    Permission.manage_transfers: "Preparar y enviar traslados",
    Permission.declare_reception: "Declarar la recepción",
    Permission.manage_users: "Administrar usuarios",
}
FIELD_ERRORS = {
    "email": "Escribe un correo válido.",
    "full_name": "Escribe el nombre completo.",
    "password": "La contraseña necesita al menos 12 caracteres.",
    "role": "Elige un rol.",
}
NO_ACCESS = ("Sin acceso", "Solo un administrador puede gestionar usuarios.")
ASK_ADMIN = "Si necesitas crear cuentas o cambiar roles, pídelo a un administrador de ECON."
PAGE_NOTE = (
    "Alta de cuentas, cambio de rol, activación y contraseña. Cada cambio se guarda al "
    "confirmarlo y se aplica a las sesiones abiertas del usuario."
)
CREATE_NOTE = "La cuenta queda activa y puede entrar en cuanto se crea."
EDIT_RULES = (
    "Un administrador no puede desactivar su propia cuenta ni dejar el sistema sin "
    "ningún administrador activo."
)
ROLE_FIELD_NOTE = "Decide qué consulta y qué puede registrar; ver Roles y permisos."
PASSWORD_NOTE = "Mínimo 12 caracteres. Entrégala por un canal seguro: no vuelve a mostrarse."
ACTIVE_NOTE = "Una cuenta inactiva no puede entrar y pierde sus sesiones abiertas."
TABLE_HEADERS = ["Usuario", "Correo", "Rol", "Estado", "Alta", "Acción"]


def admin_user() -> User | None:
    user = current_user()
    return user if user is not None and can(user.role, Permission.manage_users) else None


def is_admin() -> bool:
    return admin_user() is not None


def no_access():
    """Same wording as the API, with the role that carries the permission and what to do."""
    return permission_note(NO_ACCESS[0], NO_ACCESS[1], guidance=ASK_ADMIN)


def field(identifier: str, label: str, **props):
    return dmc.TextInput(id=identifier, label=label, autoComplete="off", **props)


def role_select(identifier: str, value: str | None = None, **props):
    return dmc.Select(
        id=identifier, label="Rol", data=ROLE_OPTIONS, value=value, allowDeselect=False, **props
    )


def password_input(identifier: str, label: str, description: str):
    return dmc.PasswordInput(
        id=identifier,
        label=label,
        description=description,
        autoComplete="new-password",
        visibilityToggleButtonProps={"aria-label": "Mostrar u ocultar la contraseña"},
    )


def role_reference():
    """What each role may do, built from the permission rules instead of a copied list."""
    rows = [
        [
            ROLE_LABELS[role],
            ", ".join(PERMISSION_LABELS[permission] for permission in permissions_of(role)),
        ]
        for role in Role
    ]
    return simple_table(["Rol", "Qué puede hacer"], rows, caption="Permisos de cada rol")


def new_user_form():
    return dmc.Stack(
        [
            dmc.SimpleGrid(
                [
                    field(
                        "new-name",
                        "Nombre completo",
                        description="Queda como autor de las acciones que registre.",
                        required=True,
                    ),
                    field(
                        "new-email",
                        "Correo",
                        description="Con él inicia sesión; se guarda en minúsculas y no se repite.",
                        inputProps={"type": "email"},
                        required=True,
                    ),
                    role_select(
                        "new-role",
                        Role.lectura.value,
                        description=ROLE_FIELD_NOTE,
                    ),
                    password_input(
                        "new-password",
                        "Contraseña",
                        PASSWORD_NOTE,
                    ),
                ],
                cols={"base": 1, "sm": 2},
                spacing="lg",
                verticalSpacing="md",
                className="admin-form-grid",
            ),
            dmc.Group(
                [
                    dmc.Button(
                        "Crear usuario",
                        id="user-create",
                        n_clicks=0,
                        leftSection=icon("user-plus", 16),
                    ),
                    dmc.Text(CREATE_NOTE, size="xs", c="dimmed"),
                ],
                gap="md",
                align="center",
            ),
        ],
        gap="md",
        className="admin-form",
    )


def user_modal():
    return dmc.Modal(
        dmc.Stack(
            [
                html.Div(
                    [
                        eyebrow("Cuenta"),
                        dmc.Text(id="user-email", size="sm", fw=500),
                    ],
                    className="admin-modal-account",
                ),
                field("user-name", "Nombre completo", required=True),
                role_select(
                    "user-role",
                    description="El nuevo rol se aplica en la siguiente petición del usuario.",
                ),
                dmc.Switch(
                    id="user-active",
                    label="Cuenta activa",
                    description=ACTIVE_NOTE,
                    checked=True,
                ),
                password_input(
                    "user-password",
                    "Nueva contraseña (opcional)",
                    "Déjala vacía para no cambiarla. Mínimo 12 caracteres; al cambiarla se "
                    "cierran las sesiones abiertas del usuario.",
                ),
                hint(EDIT_RULES),
                dmc.Group(
                    dmc.Button(
                        "Guardar cambios",
                        id="user-save",
                        n_clicks=0,
                        leftSection=icon("device-floppy", 16),
                    ),
                    justify="flex-end",
                ),
            ],
            gap="md",
        ),
        id="user-modal",
        title="Editar usuario",
        opened=False,
        closeButtonProps={"aria-label": "Cerrar"},
        className="admin-modal",
    )


def created_at(user) -> str:
    stamp = user.created_at
    return instant(stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC))


def users_table(users: list) -> dmc.TableScrollContainer:
    rows = [
        dmc.TableTr(
            [
                dmc.TableTd(user.full_name, className="admin-user-name"),
                dmc.TableTd(user.email, className="admin-user-email"),
                dmc.TableTd(ROLE_LABELS.get(user.role, user.role)),
                dmc.TableTd("Activo" if user.is_active else "Inactivo"),
                dmc.TableTd(created_at(user), className="admin-user-date"),
                dmc.TableTd(
                    dmc.Button(
                        "Editar",
                        id={"type": "user-edit", "user": user.id},
                        n_clicks=0,
                        variant="default",
                        size="compact-sm",
                        **{"aria-label": f"Editar a {user.full_name}"},
                    ),
                    className="admin-user-action",
                ),
            ]
        )
        for user in users
    ]
    return dmc.TableScrollContainer(
        dmc.Table(
            [
                dmc.TableCaption("Usuarios registrados", className="sr-only"),
                dmc.TableThead(dmc.TableTr([dmc.TableTh(label) for label in TABLE_HEADERS])),
                dmc.TableTbody(rows),
            ],
            highlightOnHover=True,
            verticalSpacing="sm",
            fz="sm",
            className="admin-users-table",
        ),
        minWidth=720,
        type="native",
        **{"aria-label": "Usuarios registrados"},
    )


def admin_layout():
    return [
        heading("Usuarios", PAGE_NOTE),
        dcc.Store(id="admin-result", storage_type="memory"),
        dcc.Store(id="user-edit-id", storage_type="memory"),
        html.Div(id="admin-feedback", **{"aria-live": "polite"}),
        html.Div(id="admin-users", className="admin-users"),
        section("Crear usuario", new_user_form()),
        section(
            "Roles y permisos",
            hint("El rol decide qué ve y qué puede registrar cada cuenta."),
            role_reference(),
        ),
        user_modal(),
    ]


def admin_page(_hub=None, _context=None, _workflow=None):
    """Signature matches the page registry; the page reads users, not the hub."""
    if not is_admin():
        return [heading("Administración"), no_access()]
    return admin_layout()


def _message(error: Exception) -> str:
    if isinstance(error, HTTPException):
        return str(error.detail)
    if isinstance(error, ValidationError):
        location = error.errors()[0].get("loc") or ("",)
        return FIELD_ERRORS.get(str(location[0]), "Revisa los datos del formulario.")
    return "No se pudo completar la operación. Actualiza la página e intenta de nuevo."


def register_admin_callbacks(dashboard, server) -> None:
    # The API handlers only read request.app.state.engine; the session comes from the cookie.
    request = SimpleNamespace(app=server)

    @dashboard.callback(
        Output("admin-users", "children"),
        Output("admin-feedback", "children"),
        Input("admin-result", "data"),
    )
    def list_view(result):
        if not is_admin():
            return no_access(), None
        feedback = None
        if isinstance(result, dict) and result.get("message"):
            ok = bool(result.get("ok"))
            feedback = notice(
                "Cambio guardado" if ok else "Cambio no aplicado", result["message"], error=not ok
            )
        return users_table(list_users(request)), feedback

    @dashboard.callback(
        Output("user-modal", "opened"),
        Output("user-edit-id", "data"),
        Output("user-email", "children"),
        Output("user-name", "value"),
        Output("user-role", "value"),
        Output("user-active", "checked"),
        Output("user-password", "value"),
        Input({"type": "user-edit", "user": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def open_editor(clicks):
        trigger = ctx.triggered_id
        if not isinstance(trigger, dict) or not any(clicks) or not is_admin():
            return (no_update,) * 7
        with Session(server.state.engine) as db:
            user = db.get(User, trigger["user"])
        if user is None:
            return (no_update,) * 7
        return True, user.id, user.email, user.full_name, user.role, user.is_active, ""

    @dashboard.callback(
        Output("admin-result", "data"),
        Output("user-modal", "opened", allow_duplicate=True),
        Output("new-name", "value"),
        Output("new-email", "value"),
        Output("new-password", "value"),
        Input("user-create", "n_clicks"),
        Input("user-save", "n_clicks"),
        State("new-name", "value"),
        State("new-email", "value"),
        State("new-role", "value"),
        State("new-password", "value"),
        State("user-edit-id", "data"),
        State("user-name", "value"),
        State("user-role", "value"),
        State("user-active", "checked"),
        State("user-password", "value"),
        prevent_initial_call=True,
    )
    def save(create_clicks, save_clicks, name, email, role, password, user_id, *edited):
        actor = admin_user()
        keep = (no_update,) * 3
        if actor is None:
            return {"ok": False, "message": NO_ACCESS[1]}, no_update, *keep
        try:
            if ctx.triggered_id == "user-create" and create_clicks:
                data = UserCreate(
                    email=email or "", full_name=name or "", role=role, password=password or ""
                )
                created = create_user(request, data)
                message = f"Usuario {created.email} creado con rol {ROLE_LABELS[Role(role)]}."
                return {"ok": True, "message": message}, no_update, "", "", ""
            if ctx.triggered_id == "user-save" and save_clicks and user_id is not None:
                edited_name, edited_role, active, new_password = edited
                data = UserUpdate(
                    full_name=edited_name or "",
                    role=edited_role,
                    is_active=bool(active),
                    password=new_password or None,
                )
                updated = update_user(request, int(user_id), data, actor)
                message = f"Usuario {updated.email} actualizado."
                return {"ok": True, "message": message}, False, *keep
        except (HTTPException, ValidationError, ValueError, TypeError) as error:
            return {"ok": False, "message": _message(error)}, no_update, *keep
        return (no_update,) * 5

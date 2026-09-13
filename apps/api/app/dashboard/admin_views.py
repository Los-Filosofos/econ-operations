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
from app.core.auth import Permission, Role, can
from app.dashboard.analytics import instant
from app.dashboard.auth_views import ROLE_LABELS, current_user
from app.dashboard.components import accordion, disclosure, heading, icon, notice
from app.models.users import User

ROLE_OPTIONS = [{"value": role.value, "label": ROLE_LABELS[role]} for role in Role]
FIELD_ERRORS = {
    "email": "Escribe un correo válido.",
    "full_name": "Escribe el nombre completo.",
    "password": "La contraseña necesita al menos 12 caracteres.",
    "role": "Elige un rol.",
}
NO_ACCESS = ("Sin acceso", "Solo un administrador puede gestionar usuarios.")


def admin_user() -> User | None:
    user = current_user()
    return user if user is not None and can(user.role, Permission.manage_users) else None


def is_admin() -> bool:
    return admin_user() is not None


def field(identifier: str, label: str, **props):
    return dmc.TextInput(id=identifier, label=label, autoComplete="off", **props)


def role_select(identifier: str, value: str | None = None):
    return dmc.Select(
        id=identifier, label="Rol", data=ROLE_OPTIONS, value=value, allowDeselect=False
    )


def password_input(identifier: str, label: str, description: str):
    return dmc.PasswordInput(
        id=identifier,
        label=label,
        description=description,
        autoComplete="new-password",
        visibilityToggleButtonProps={"aria-label": "Mostrar u ocultar la contraseña"},
    )


def new_user_form():
    return dmc.Stack(
        [
            dmc.SimpleGrid(
                [
                    field("new-name", "Nombre completo", required=True),
                    field("new-email", "Correo", inputProps={"type": "email"}, required=True),
                    role_select("new-role", Role.lectura.value),
                    password_input("new-password", "Contraseña", "Mínimo 12 caracteres."),
                ],
                cols={"base": 1, "xs": 2},
                spacing="md",
            ),
            dmc.Group(
                dmc.Button(
                    "Crear usuario",
                    id="user-create",
                    n_clicks=0,
                    leftSection=icon("user-plus", 16),
                )
            ),
        ],
        gap="md",
    )


def user_modal():
    return dmc.Modal(
        dmc.Stack(
            [
                dmc.Text(id="user-email", size="sm", c="dimmed"),
                field("user-name", "Nombre completo", required=True),
                role_select("user-role"),
                dmc.Switch(id="user-active", label="Cuenta activa", checked=True),
                password_input(
                    "user-password",
                    "Nueva contraseña (opcional)",
                    "Mínimo 12 caracteres; cierra las sesiones abiertas del usuario.",
                ),
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
    )


def users_table(users: list) -> dmc.TableScrollContainer:
    rows = [
        dmc.TableTr(
            [
                dmc.TableTd(
                    [
                        html.Span(
                            user.full_name,
                            title="Creado: "
                            + instant(
                                user.created_at
                                if user.created_at.tzinfo
                                else user.created_at.replace(tzinfo=UTC)
                            ),
                        ),
                        dmc.Text(user.email, size="xs", c="dimmed"),
                    ]
                ),
                dmc.TableTd(ROLE_LABELS.get(user.role, user.role)),
                dmc.TableTd("Activo" if user.is_active else "Inactivo"),
                dmc.TableTd(
                    dmc.Button(
                        "Editar",
                        id={"type": "user-edit", "user": user.id},
                        n_clicks=0,
                        variant="subtle",
                        size="compact-sm",
                        **{"aria-label": f"Editar a {user.full_name}"},
                    )
                ),
            ]
        )
        for user in users
    ]
    return dmc.TableScrollContainer(
        dmc.Table(
            [
                dmc.TableCaption("Usuarios registrados", className="sr-only"),
                dmc.TableThead(
                    dmc.TableTr(
                        [dmc.TableTh(label) for label in ["Usuario", "Rol", "Estado", "Acción"]]
                    )
                ),
                dmc.TableTbody(rows),
            ],
            highlightOnHover=True,
            verticalSpacing="xs",
            fz="sm",
        ),
        minWidth=500,
        type="native",
        **{"aria-label": "Usuarios registrados"},
    )


def admin_layout():
    return [
        heading("Usuarios"),
        dcc.Store(id="admin-result", storage_type="memory"),
        dcc.Store(id="user-edit-id", storage_type="memory"),
        html.Div(id="admin-feedback", **{"aria-live": "polite"}),
        html.Div(id="admin-users"),
        accordion(disclosure("Crear usuario", new_user_form())),
        user_modal(),
    ]


def admin_page(_hub=None, _context=None, _workflow=None):
    """Signature matches the page registry; the page reads users, not the hub."""
    if not is_admin():
        return [heading("Administración"), notice(*NO_ACCESS, error=True)]
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
            return notice(*NO_ACCESS, error=True), None
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

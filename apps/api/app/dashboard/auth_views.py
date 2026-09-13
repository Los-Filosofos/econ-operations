"""Login page, header identity and permission helpers for the Dash views.

The browser never decides anything: the login form posts to the API from a clientside
callback, and every server callback re-reads the session before rendering or acting.
"""

from urllib.parse import parse_qs, quote

import dash_mantine_components as dmc
from dash import Input, Output, State, dcc, html
from dash.exceptions import DashException

from app.core.auth import Permission, Role, can, session_user
from app.dashboard.components import eyebrow, icon
from app.dashboard.theme import FAMILY_COLORS, PAPER, SURFACE
from app.models.users import User

ROLE_LABELS = {
    Role.admin: "Administrador",
    Role.gerencia_proyecto: "Gerencia de Proyecto",
    Role.logistica: "Logística y Equipo",
    Role.mantenimiento: "Mantenimiento",
    Role.control_costos: "Control de Costos",
    Role.lectura: "Lectura",
}
DENIED = "Tu rol no permite esta acción"
ROLE_CHANGE = "Un administrador puede cambiar tu rol desde Administración."
# The only product sentence on the login screen: what the hub holds, in plain terms.
PRODUCT_LINE = (
    "Reúne las solicitudes y la maquinaria leídas de Prisma, los traslados enviados a "
    "Startrack y el historial de cada movimiento."
)
ACCOUNT_NOTE = "Las cuentas y los roles los crea un administrador de ECON."
# Mirrors the 429 the API returns after repeated failures from the same address.
ATTEMPTS_NOTE = (
    "Tras varios intentos fallidos el servidor deja de aceptar intentos durante unos minutos."
)
LOGIN_JS = """
async function(clicks, emailSubmit, passwordSubmit, email, password, next) {
  const noUpdate = window.dash_clientside.no_update;
  if (!clicks && !emailSubmit && !passwordSubmit) { return [noUpdate, "none"]; }
  if (!email || !password) { return ["Escribe tu correo y tu contraseña.", "block"]; }
  window.dash_clientside.set_props("login-submit", {loading: true});
  let message = "No se pudo iniciar sesión. Intenta de nuevo.";
  try {
    const response = await fetch("/api/v1/auth/login", {
      method: "POST",
      credentials: "same-origin",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({email: email.trim(), password: password}),
    });
    if (response.ok) { window.location.assign(next || "/"); return [noUpdate, "none"]; }
    if (response.status === 401) { message = "Correo o contraseña incorrectos"; }
    else if (response.status === 429) { message = "Demasiados intentos; espera unos minutos"; }
    else if (response.status === 422) { message = "Escribe un correo válido."; }
  } catch (error) {
    message = "No se pudo contactar con el servidor.";
  }
  window.dash_clientside.set_props("login-submit", {loading: false});
  return [message, "block"];
}
"""
LOGOUT_JS = """
async function(clicks) {
  if (!clicks) { return window.dash_clientside.no_update; }
  try {
    await fetch("/api/v1/auth/logout", {method: "POST", credentials: "same-origin"});
  } finally {
    window.location.assign("/login");
  }
  return true;
}
"""


def current_user() -> User | None:
    """Session user for a view; None when anonymous or when there is no Dash request."""
    try:
        return session_user()
    except DashException:
        return None


def permitted(permission: Permission) -> bool:
    """Whether the acting role may see an action; without a session the local dev mode decides."""
    user = current_user()
    return user is None or can(user.role, permission)


def roles_allowed(permission: Permission) -> str:
    """Names of the roles that hold a permission, read from the rules in core.auth."""
    return ", ".join(ROLE_LABELS[role] for role in Role if can(role, permission))


def permission_note(title: str, detail: str, *, guidance: str = ROLE_CHANGE):
    """Plain block that names who may act and what to do; no alert colors, no icons."""
    user = current_user()
    acting = (
        f"Tu sesión actúa como {ROLE_LABELS.get(user.role, user.role)}."
        if user is not None
        else None
    )
    return html.Div(
        [
            dmc.Text(title, size="sm", fw=600, className="permission-title"),
            dmc.Text(detail, size="sm", className="permission-detail"),
            dmc.Text(
                " ".join(filter(None, (acting, guidance))), size="xs", className="permission-next"
            ),
        ],
        className="permission-note",
        role="status",
    )


def denied(permission: Permission | None = None):
    """Why this control is absent for the acting role, and which role carries it."""
    if permission is None:
        detail = (
            "Preparar y enviar traslados corresponde a: "
            f"{roles_allowed(Permission.manage_transfers)}. Declarar la recepción, a: "
            f"{roles_allowed(Permission.declare_reception)}."
        )
    else:
        detail = f"Corresponde a: {roles_allowed(permission)}."
    return permission_note(DENIED, detail)


def safe_next(search: str | None) -> str:
    """Only an internal, relative path may follow the login; anything else lands on /."""
    target = parse_qs((search or "").lstrip("?")).get("next", ["/"])[0]
    if not target.startswith("/") or target.startswith("//") or "\\" in target:
        return "/"
    return target


def login_target(path: str, search: str | None) -> str:
    return "/login?next=" + quote(path + (search or ""), safe="")


def redirect(href: str):
    return dcc.Location(id="login-redirect", href=href, refresh=True)


def login_identity():
    """Left column: who this is and what the hub holds. One sentence, no illustration."""
    return html.Div(
        [
            html.Img(
                src="/assets/econ-color.png", alt="Grupo ECON", height=36, className="login-logo"
            ),
            eyebrow("Centro de operaciones"),
            dmc.Title("Control de maquinaria", order=1, size="h2", className="login-title"),
            dmc.Text(PRODUCT_LINE, className="login-line"),
            dmc.Text(ACCOUNT_NOTE, className="login-note"),
        ],
        className="login-identity-inner",
    )


def login_form(search: str | None):
    """Right column: labelled fields, the error beside them and one primary action."""
    return html.Main(
        [
            dmc.Title("Iniciar sesión", order=2, size="h4", className="login-form-title"),
            dmc.TextInput(
                id="login-email",
                label="Correo",
                inputProps={"type": "email", "autoFocus": True},
                autoComplete="username",
                required=True,
                withAsterisk=False,
                size="md",
                className="login-field",
            ),
            dmc.PasswordInput(
                id="login-password",
                label="Contraseña",
                autoComplete="current-password",
                required=True,
                withAsterisk=False,
                size="md",
                className="login-field",
                visibilityToggleButtonProps={"aria-label": "Mostrar u ocultar la contraseña"},
            ),
            # The clientside callback writes the text and toggles its display; it stays
            # next to the fields it talks about instead of floating in a banner.
            html.Div(
                dmc.Text(
                    id="login-error",
                    display="none",
                    size="sm",
                    c=FAMILY_COLORS["issue"],
                    className="login-error",
                ),
                className="login-error-slot",
                role="alert",
            ),
            dmc.Button(
                "Entrar",
                id="login-submit",
                n_clicks=0,
                fullWidth=True,
                size="md",
                className="login-submit",
            ),
            dmc.Text(ATTEMPTS_NOTE, className="login-hint"),
            dcc.Store(id="login-next", data=safe_next(search)),
        ],
        id="login-main",
        className="login-form",
    )


def login_page(search: str | None):
    """Two columns on a desktop, stacked on a phone; no floating card, no gradient.

    The surfaces are also set inline from the theme so a cold first load still shows the
    two panels while z-auth.css refines their rules and spacing.
    """
    return html.Div(
        dmc.Grid(
            [
                dmc.GridCol(
                    login_identity(), span={"base": 12, "md": 7}, className="login-identity"
                ),
                dmc.GridCol(
                    login_form(search),
                    span={"base": 12, "md": 5},
                    bg=PAPER,
                    className="login-panel",
                ),
            ],
            gutter=0,
            className="login-grid",
        ),
        className="login-page",
        style={"background": SURFACE, "minHeight": "100vh"},
    )


def header_user(user: User | None, auth_required: bool):
    """Who is signed in and how to leave: plain text plus one labelled control."""
    if user is None:
        text = "Sesión local sin autenticación" if not auth_required else "Sin sesión"
        return dmc.Text(text, size="xs", className="econ-session-note", visibleFrom="xs")
    return dmc.Group(
        [
            dmc.Stack(
                [
                    dmc.Text(user.full_name, size="sm", fw=600, className="econ-session-name"),
                    dmc.Text(
                        ROLE_LABELS.get(user.role, user.role),
                        size="xs",
                        className="econ-session-role",
                    ),
                ],
                gap=0,
                visibleFrom="sm",
                className="econ-session",
            ),
            dmc.Button(
                [
                    dmc.Text("Cerrar sesión", span=True, size="sm", visibleFrom="xs"),
                    dmc.Text("Salir", span=True, size="sm", hiddenFrom="xs"),
                ],
                id="logout",
                n_clicks=0,
                variant="default",
                size="xs",
                leftSection=icon("logout", 16),
                className="econ-logout",
            ),
        ],
        gap="sm",
        wrap="nowrap",
        className="econ-session-group",
    )


def register_auth_callbacks(dashboard) -> None:
    dashboard.clientside_callback(
        LOGIN_JS,
        Output("login-error", "children"),
        Output("login-error", "display"),
        Input("login-submit", "n_clicks"),
        Input("login-email", "n_submit"),
        Input("login-password", "n_submit"),
        State("login-email", "value"),
        State("login-password", "value"),
        State("login-next", "data"),
        prevent_initial_call=True,
    )
    dashboard.clientside_callback(
        LOGOUT_JS,
        Output("logout", "disabled"),
        Input("logout", "n_clicks"),
        prevent_initial_call=True,
    )

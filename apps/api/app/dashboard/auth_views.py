"""Login page, header identity and permission helpers for the Dash views.

The browser never decides anything: the login form posts to the API from a clientside
callback, and every server callback re-reads the session before rendering or acting.
"""

from urllib.parse import parse_qs, quote

import dash_mantine_components as dmc
from dash import Input, Output, State, dcc, html
from dash.exceptions import DashException

from app.core.auth import Permission, Role, can, session_user
from app.dashboard.components import hint, icon
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


def denied():
    return hint(DENIED, role="status")


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


def login_page(search: str | None):
    return dmc.Center(
        html.Main(
            dmc.Paper(
                [
                    dmc.Stack(
                        [
                            html.Img(src="/assets/econ-color.png", alt="Grupo ECON", height=40),
                            dmc.Title("Iniciar sesión", order=1, size="h3"),
                            dmc.Text(
                                "Control de maquinaria · acceso con cuenta de usuario",
                                size="sm",
                                c="dimmed",
                            ),
                        ],
                        gap=6,
                        align="center",
                        mb="lg",
                    ),
                    dmc.Stack(
                        [
                            dmc.TextInput(
                                id="login-email",
                                label="Correo",
                                inputProps={"type": "email"},
                                autoComplete="username",
                                required=True,
                                leftSection=icon("mail", 16),
                            ),
                            dmc.PasswordInput(
                                id="login-password",
                                label="Contraseña",
                                autoComplete="current-password",
                                required=True,
                                leftSection=icon("lock", 16),
                                visibilityToggleButtonProps={
                                    "aria-label": "Mostrar u ocultar la contraseña"
                                },
                            ),
                            dmc.Alert(
                                id="login-error",
                                color="red",
                                variant="light",
                                icon=icon("alert-circle"),
                                display="none",
                            ),
                            dmc.Button(
                                "Entrar",
                                id="login-submit",
                                n_clicks=0,
                                fullWidth=True,
                                leftSection=icon("login", 16),
                            ),
                        ],
                        gap="md",
                    ),
                    dcc.Store(id="login-next", data=safe_next(search)),
                ],
                withBorder=True,
                p="xl",
                w="100%",
                maw=400,
                className="login-card",
            ),
            id="login-main",
        ),
        mih="100vh",
        p="md",
        bg="gray.0",
    )


def header_user(user: User | None, auth_required: bool):
    if user is None:
        text = "Sesión local sin autenticación" if not auth_required else "Sin sesión"
        return dmc.Text(text, size="xs", c="dimmed", visibleFrom="xs")
    role = ROLE_LABELS.get(user.role, user.role)
    return dmc.Menu(
        [
            dmc.MenuTarget(
                dmc.Button(
                    [
                        dmc.Text(user.full_name, size="sm", fw=500, visibleFrom="sm"),
                        dmc.Badge(role, size="xs", variant="light", visibleFrom="sm"),
                    ],
                    id="user-menu",
                    variant="subtle",
                    color="gray",
                    size="sm",
                    leftSection=icon("user-circle", 20),
                    rightSection=icon("chevron-down", 14),
                    **{"aria-label": f"Cuenta de {user.full_name}"},
                )
            ),
            dmc.MenuDropdown(
                [
                    dmc.MenuLabel(f"{user.full_name} · {role}"),
                    dmc.MenuLabel(user.email),
                    dmc.MenuDivider(),
                    dmc.MenuItem(
                        "Cerrar sesión",
                        id="logout",
                        n_clicks=0,
                        leftSection=icon("logout", 16),
                    ),
                ]
            ),
        ],
        shadow="md",
        width=240,
        position="bottom-end",
        keepMounted=True,
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

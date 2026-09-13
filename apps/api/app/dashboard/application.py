"""Dash on the existing FastAPI server, using the shared Python read service."""

import json
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

import dash_mantine_components as dmc
from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update
from fastapi import FastAPI
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.dashboard.admin_views import admin_layout, admin_page, register_admin_callbacks
from app.dashboard.auth_views import (
    current_user,
    header_user,
    login_page,
    login_target,
    redirect,
    register_auth_callbacks,
)
from app.dashboard.components import icon, link, loading, notice
from app.dashboard.context import QueryContext, parse_context
from app.dashboard.integration_views import (
    PANEL_PATTERN,
    SELECT_PATTERN,
    integration_controls,
    trace_panel,
)
from app.dashboard.theme import (
    BRAND,
    FAMILY_COLORS,
    MANTINE_THEME,
    PAPER,
    SHELL_VARIABLES,
)
from app.dashboard.views import (
    REQUEST_FILTERS,
    filter_tabs,
    navigation,
    origin_line,
    render_page,
    scope,
    searchable,
    workflow_page,
)
from app.dashboard.workflow_actions import WorkflowInputError, execute_action
from app.dashboard.workflow_forms import action_button, plan_form, receipt_form
from app.models.hub import HubResponse
from app.models.workflow import WorkflowOverview
from app.services.hub import read_hub
from app.services.workflow import WorkflowError

ASSETS = Path(__file__).parent / "assets"
# Order matters: the per-area sheets refine the base one, so style.css is linked first and
# the z-prefixed sheets follow in name order. Linking them explicitly means a cold deep link
# arrives styled, instead of waiting for Dash to scan the assets directory.
STYLESHEET_PATTERN = r"(?:style|z-[\w-]+)\.css"


def stylesheets() -> tuple[str, ...]:
    return ("style.css", *sorted(path.name for path in ASSETS.glob("z-*.css")))


def stylesheet_links() -> list[str]:
    """One content hash per sheet, so a deploy only invalidates the file that changed."""
    return [
        f"/assets/{name}?v={sha256((ASSETS / name).read_bytes()).hexdigest()[:12]}"
        for name in stylesheets()
    ]


INDEX = """<!DOCTYPE html>
<html lang="es">
  <head>
    {%metas%}
    <title>{%title%}</title>
    <link rel="icon" type="image/png" href="/assets/econ-icon.png">
    {%css%}
  </head>
  <body>
    {%app_entry%}
    <footer>{%config%}{%scripts%}{%renderer%}</footer>
  </body>
</html>"""
READ_ERROR = "No se pudo completar la consulta. Se reintenta al volver a leer."
WORKFLOW_READ_ERROR = (
    "No se pudo consultar el registro de movimientos. Se reintenta al volver a leer."
)
INPUT_ERROR = (
    "Revisa los campos obligatorios y los IDs. Usa fecha AAAA-MM-DD y hora HH:MM; "
    "separa los IDs de usuarios con comas."
)
ACTION_ERROR = (
    "No se pudo completar la acción. Actualiza el registro para consultar su estado "
    "antes de repetirla."
)
# The page polls GET /api/v1/status this often and reloads data only when the registry
# version changed (stale-while-revalidate: what is on screen stays until the new read lands).
STATUS_POLL_SECONDS = 15
AGO_JS = """
  const ago = (iso) => {
    const t = Date.parse(iso || "");
    if (!Number.isFinite(t)) { return "sin fecha"; }
    const s = Math.max(0, Math.round((Date.now() - t) / 1000));
    if (s < 45) { return "hace un momento"; }
    const m = Math.round(s / 60);
    if (m < 60) { return "hace " + m + " min"; }
    const h = Math.round(m / 60);
    if (h < 24) { return "hace " + h + " h"; }
    const at = new Date(t);
    return "el " + at.toLocaleDateString("es") + " " +
      at.toLocaleTimeString("es", {hour: "2-digit", minute: "2-digit"});
  };
  const modeOf = (search) => new URLSearchParams(search || "").get("mode") || "fixture";
"""
# Polls the status endpoint; pauses while the tab is hidden and polls at once when it returns.
# `registry` is written only when a store of the current mode carries another version.
STATUS_JS = (
    """
async function(ticks, search, snapshot, workflow, hubLoading, workflowLoading) {
  const noUpdate = window.dash_clientside.no_update;
  const path = window.location.pathname.replace(/[/]$/, "") || "/";
  if (path === "/administracion") { return [noUpdate, noUpdate]; }
  const usesHub = path !== "/operaciones" && !path.startsWith("/operaciones/");
  if (!window.econVisibilityWatch) {
    window.econVisibilityWatch = true;
    document.addEventListener("visibilitychange", () => {
      if (!document.getElementById("application-shell")) { return; }
      const hidden = document.visibilityState === "hidden";
      const props = {disabled: hidden};
      if (!hidden) { props.n_intervals = (window.econPollTicks || 0) + 1; }
      window.dash_clientside.set_props("status-poll", props);
    });
  }
  window.econPollTicks = ticks || 0;
  if (document.visibilityState === "hidden") { return [noUpdate, noUpdate]; }
"""
    + AGO_JS
    + """
  const mode = modeOf(search);
  let status;
  try {
    const response = await fetch("/api/v1/status?mode=" + encodeURIComponent(mode), {
      credentials: "same-origin", cache: "no-store", headers: {Accept: "application/json"},
    });
    if (response.status === 401) {
      const next = window.location.pathname + window.location.search;
      window.location.assign("/login?next=" + encodeURIComponent(next));
      return [noUpdate, noUpdate];
    }
    if (!response.ok) { throw new Error(String(response.status)); }
    status = await response.json();
  } catch (error) {
    status = {mode: mode, error: "Sin respuesta del servidor"};
  }
  status.checked_at = new Date().toISOString();
  const version = status.registry_version;
  const stale = (store) => Boolean(store) && typeof store === "object" &&
    store.mode === mode && store.version !== version;
  const registry = version && !hubLoading && !workflowLoading &&
    ((usesHub && stale(snapshot)) || stale(workflow))
    ? {mode: mode, version: version, at: Date.now()}
    : noUpdate;
  return [status, registry];
}
"""
)
# Header text and the details behind it, recomputed on every tick so "hace X min" moves.
HEADER_JS = (
    """
function(ticks, snapshot, status, path, search) {
  const colors = %s;
"""
    + AGO_JS
    + """
  const mode = modeOf(search);
  const mine = Boolean(snapshot) && typeof snapshot === "object" && snapshot.mode === mode;
  let text = "Leyendo el origen…";
  let short = "leyendo…";
  let state = "neutral";
  if (mine && snapshot.hub && mode === "fixture") {
    short = "Muestra";
    text = "Muestra documental";
  } else if (mine && snapshot.hub && snapshot.hub.data_as_of) {
    short = ago(snapshot.hub.data_as_of);
    text = "Última lectura " + short;
    state = "active";
  } else if (mine && snapshot.error) {
    text = "Última consulta sin respuesta";
    short = "sin respuesta";
    state = "issue";
  }
  const current = status && typeof status === "object" && status.mode === mode ? status : null;
  if (path === "/operaciones" || (path || "").startsWith("/operaciones/")) {
    short = current && current.registry_last_read_at
      ? ago(current.registry_last_read_at) : "Sin lectura confirmada";
    text = current && current.registry_last_read_at ? "Registro leído " + short : short;
    state = "neutral";
  }
  let registry = "Registro del servidor sin comprobar todavía.";
  let sync = "";
  let poll = "Comprobación del registro cada %d s.";
  if (current && current.error) {
    registry = "Sin respuesta del servidor al comprobar el registro.";
    poll = "Última comprobación fallida " + ago(current.checked_at) + ".";
    state = "issue";
  } else if (current) {
    registry = current.registry_last_read_at
      ? "Origen sincronizado " + ago(current.registry_last_read_at) + "."
      : "Sin sincronización guardada para este origen.";
    poll = "Registro comprobado " + ago(current.checked_at) + " · cada %d s.";
    const cycle = current.sync || {};
    if (mode !== "live") {
      sync = "Origen local: los cambios provienen del registro de esta base.";
    } else if (!cycle.enabled) {
      sync = "Sincronización automática desactivada.";
    } else {
      const outcome = cycle.last_cycle_result === "ok" ? "correcta"
        : cycle.last_cycle_result === "skipped" ? "omitida: otro proceso sincronizaba"
        : cycle.last_cycle_result || "";
      sync = "Sincronización automática cada " + cycle.interval_seconds + " s" +
        (cycle.last_cycle_at
          ? " · último ciclo " + ago(cycle.last_cycle_at) + " · " + outcome
          : " · sin ciclo todavía") + ".";
    }
    if (cycle.in_progress) { sync += " Sincronizando ahora…"; }
  }
  return [text, short, {background: colors[state]}, registry, sync, poll];
}
"""
)
# The accessible fallback: an explicit re-read, forced regardless of the version.
REREAD_JS = """
function(clicks, search) {
  if (!clicks) { return window.dash_clientside.no_update; }
  const mode = new URLSearchParams(search || "").get("mode") || "fixture";
  return {mode: mode, version: null, forced: true, at: Date.now()};
}
"""


# Pattern ids: only the list pages mount the bar, and its callbacks still register.
SEARCH_ID = {"type": "query-search", "field": "q"}
APPLY_ID = {"type": "query-apply", "field": "apply"}
SEARCH_PATTERN = {"type": "query-search", "field": ALL}
APPLY_PATTERN = {"type": "query-apply", "field": ALL}


def query_controls(context: QueryContext | None = None, path: str = "/solicitudes"):
    """A list-specific search, mounted beneath that list's heading."""
    context = context or QueryContext()
    label, placeholder = {
        "/solicitudes": ("Buscar solicitudes", "Proyecto, solicitud o unidad"),
        "/maquinaria": ("Buscar maquinaria", "Código, nombre o proyecto"),
        "/operaciones": ("Buscar en esta página de movimientos", "Referencia, proyecto o ID"),
    }.get(path, ("Buscar solicitudes", "Proyecto, solicitud o unidad"))
    return dmc.Group(
        [
            dmc.TextInput(
                id=SEARCH_ID,
                label=label,
                value=context.query,
                placeholder=placeholder,
                leftSection=icon("search", 16),
                autoComplete="off",
                style={"flex": 1, "minWidth": 180, "maxWidth": 440},
            ),
            dmc.Button(
                "Buscar",
                id=APPLY_ID,
                n_clicks=0,
                variant="default",
                style={"alignSelf": "flex-end"},
            ),
            link(
                "Limpiar búsqueda",
                QueryContext(mode=context.mode).href(path, filter=context.filter),
            )
            if context.query
            else None,
        ],
        align="flex-end",
        gap="sm",
        className="query-bar",
        mb="md",
    )


def list_controls(page, path: str, context: QueryContext):
    if searchable(path):
        return [page[0], query_controls(context, path), *page[1:]]
    return page


def brand(height=34):
    return dmc.Anchor(
        html.Img(src="/assets/econ-color.png", alt="Grupo ECON", height=height),
        href="/",
        className="econ-shell-logo",
        **{"aria-label": "Inicio"},
    )


def identity(height=32, *, on_phone=True):
    """One identity block: the mark carries the company, the text next to it the product."""
    product = {"className": "header-product-name", "size": "xs", "fw": 500}
    if not on_phone:
        # Phones keep the mark alone in the header; the drawer heading repeats the product.
        product["visibleFrom"] = "sm"
    return html.Div(
        [brand(height), dmc.Text("Centro de operaciones", **product)],
        className="econ-shell-identity",
    )


def layout():
    """Root shell: the route callback fills it with the login page or the application."""
    return dmc.MantineProvider(
        [
            dcc.Location(id="url", refresh="callback-nav"),
            dcc.Store(id="view", storage_type="memory"),
            html.Div(id="root"),
        ],
        theme=MANTINE_THEME,
    )


def read_status():
    """Header status instead of a refresh button: when the data on screen was read, and a menu
    with the server's synchronization state plus the accessible fallback "Volver a leer ahora"."""
    detail = {"size": "xs", "c": "dimmed", "px": "sm", "py": 4, "maw": 300}
    return dmc.Group(
        [
            html.Span(
                id="refresh-indicator",
                className="refresh-indicator",
                role="status",
                **{"aria-live": "polite"},
            ),
            dmc.Menu(
                [
                    dmc.MenuTarget(
                        dmc.Button(
                            [
                                dmc.Text(
                                    "Leyendo el origen…",
                                    id="read-status-text",
                                    span=True,
                                    size="sm",
                                    visibleFrom="sm",
                                ),
                                # Phones get the relative time only; the menu keeps the rest.
                                dmc.Text(
                                    "leyendo…",
                                    id="read-status-short",
                                    span=True,
                                    size="sm",
                                    hiddenFrom="sm",
                                ),
                            ],
                            id="read-status",
                            variant="subtle",
                            color="gray",
                            size="sm",
                            className="read-status",
                            leftSection=html.Span(
                                id="read-status-dot",
                                className="state-dot",
                                hidden=True,
                                style={"background": FAMILY_COLORS["neutral"]},
                                **{"aria-hidden": "true"},
                            ),
                            rightSection=icon("chevron-down", 14),
                            **{"aria-label": "Estado de la lectura de datos"},
                        )
                    ),
                    dmc.MenuDropdown(
                        [
                            dmc.MenuLabel("Lectura de datos"),
                            dmc.Text(id="registry-line", **detail),
                            dmc.Text(id="sync-line", **detail),
                            dmc.Text(id="poll-line", **detail),
                            dmc.MenuDivider(),
                            dmc.MenuItem(
                                "Volver a leer ahora",
                                id="refresh",
                                n_clicks=0,
                                leftSection=icon("refresh", 16),
                            ),
                        ]
                    ),
                ],
                shadow="xs",
                width=320,
                position="bottom-end",
                # Rendered next to its trigger (no portal) with focusable items: Tab reaches
                # "Volver a leer ahora" from the trigger, Escape closes and returns focus.
                withinPortal=False,
                keepMounted=True,
                menuItemTabIndex=0,
                closeOnEscape=True,
                returnFocus=True,
            ),
        ],
        gap="xs",
        wrap="nowrap",
        className="econ-shell-reading",
    )


def app_shell(auth_required: bool):
    header = dmc.AppShellHeader(
        dmc.Group(
            [
                dmc.ActionIcon(
                    icon("menu-2", 22),
                    id="burger",
                    n_clicks=0,
                    variant="subtle",
                    color="gray",
                    size="lg",
                    hiddenFrom="sm",
                    **{
                        "aria-label": "Abrir navegación",
                        "aria-controls": "mobile-navigation",
                        "aria-expanded": "false",
                    },
                ),
                identity(32, on_phone=False),
                # Reading state first, account last: the rightmost control is the session.
                dmc.Group(
                    [
                        html.Div(read_status(), id="data-status"),
                        html.Div(header_user(current_user(), auth_required), id="header-user"),
                    ],
                    gap="md",
                    ml="auto",
                    wrap="nowrap",
                    className="econ-shell-controls",
                ),
            ],
            h="100%",
            px="md",
            gap="md",
            wrap="nowrap",
        ),
        className="econ-header",
        style={"background": PAPER},
    )
    navbar = dmc.AppShellNavbar(
        [
            html.Nav(
                id="navigation",
                className="econ-nav",
                **{"aria-label": "Navegación principal"},
            ),
            # The origin of what is on screen, as text, where it stays visible while working.
            html.Div(
                [
                    html.Span("Origen de datos", className="eyebrow"),
                    # The placeholder never names an origin the callback has not read yet.
                    html.Span(
                        "Leyendo el origen…", id="navbar-origin", className="econ-shell-origin"
                    ),
                ],
                className="econ-shell-datamode",
            ),
        ],
        p=0,
        className="econ-sidebar",
        style={"background": BRAND},
    )
    stores = [
        dcc.Store(id="snapshot", storage_type="memory"),
        dcc.Store(id="workflow-snapshot", storage_type="memory"),
        dcc.Store(id="hub-loading", data=False, storage_type="memory"),
        dcc.Store(id="workflow-loading", data=False, storage_type="memory"),
        dcc.Store(id="workflow-action-result", storage_type="memory"),
    ]
    main = dmc.AppShellMain(
        dmc.Container(
            [
                # Server status poll; the stores survive navigation, so a page change never
                # re-reads while the registry version is unchanged.
                dcc.Interval(id="status-poll", interval=STATUS_POLL_SECONDS * 1000, n_intervals=0),
                dcc.Store(id="status", storage_type="memory"),
                dcc.Store(id="registry", storage_type="memory"),
                html.Div(id="scope"),
                html.Div(id="workflow-feedback", **{"aria-live": "polite"}),
                dcc.Loading(
                    [*stores, html.Main(id="content", tabIndex=-1)],
                    custom_spinner=html.P(
                        "Procesando la acción…", className="econ-shell-progress", role="status"
                    ),
                    # Only an operator action hides the page; background reads keep the
                    # previous data visible and announce "Actualizando…" in the header.
                    target_components={"workflow-action-result": "data"},
                    delay_show=150,
                    overlay_style={"visibility": "hidden"},
                ),
            ],
            size=1480,
            px=0,
        ),
        className="econ-workspace",
        style={"background": PAPER},
    )
    return html.Div(
        [
            html.A("Saltar al contenido", href="#content", className="skip-link"),
            dmc.AppShell(
                [header, navbar, main],
                header={"height": 68},
                navbar={"width": 224, "breakpoint": "sm", "collapsed": {"mobile": True}},
                padding={"base": 16, "md": 32},
            ),
            dmc.Drawer(
                html.Nav(
                    id="mobile-navigation-links",
                    className="econ-nav",
                    **{"aria-label": "Navegación principal"},
                ),
                id="mobile-navigation",
                title=identity(28),
                opened=False,
                size=280,
                padding="md",
                classNames={
                    "content": "econ-mobile-navigation",
                    "header": "econ-mobile-heading",
                    "body": "econ-mobile-body",
                },
                closeButtonProps={"aria-label": "Cerrar navegación"},
            ),
        ],
        id="application-shell",
        className="application-shell",
        style=SHELL_VARIABLES,
    )


def validation_controls():
    """Every dynamic callback ID is declared without relaxing layout validation."""
    return html.Div(
        [
            plan_form(),
            receipt_form(),
            action_button("queue", "Poner en cola"),
            action_button("sync", "Sincronizar"),
            filter_tabs(QueryContext(), REQUEST_FILTERS, "Filtros"),
            query_controls(),
            *integration_controls(),
            # The signed-in header only exists inside a request; declare its IDs here.
            dmc.Button("Cerrar sesión", id="logout", n_clicks=0),
        ]
    )


def workflow_from(snapshot, mode) -> WorkflowOverview | None:
    if not isinstance(snapshot, dict) or snapshot.get("mode") != mode:
        return None
    try:
        workflow = WorkflowOverview.model_validate(snapshot.get("overview"))
        if any(movement.mode != mode for movement in workflow.movements):
            raise ValueError("Los movimientos no corresponden al origen seleccionado.")
        return workflow
    except (ValidationError, ValueError):
        if snapshot.get("error"):
            return WorkflowOverview(available=False, message=snapshot["error"])
        return None


def create_dashboard(server: FastAPI) -> Dash:
    dashboard = Dash(
        __name__,
        server=server,
        assets_folder=str(ASSETS),
        # FastAPI catch-all routes can render before Dash's first-request asset scan.
        # Register CSS explicitly so a cold deep link is styled on its first load.
        assets_ignore=STYLESHEET_PATTERN,
        external_stylesheets=stylesheet_links(),
        title="ECON · Control de maquinaria",
        update_title="Consultando…",
        index_string=INDEX,
        suppress_callback_exceptions=False,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    )
    settings = server.state.settings
    dashboard.layout = layout
    dashboard.validation_layout = html.Div(
        [
            layout(),
            app_shell(settings.auth_required),
            login_page(None),
            redirect("/"),
            *admin_layout(),
            validation_controls(),
        ]
    )
    register_auth_callbacks(dashboard)
    register_admin_callbacks(dashboard, server)

    def anonymous() -> bool:
        return settings.auth_required and current_user() is None

    @dashboard.callback(
        Output("root", "children"),
        Output("view", "data"),
        Input("url", "pathname"),
        State("url", "search"),
        State("view", "data"),
    )
    def route(path, search, current):
        path = (path or "/").rstrip("/") or "/"
        user = current_user()
        if path == "/login":
            # Without AUTH_REQUIRED there is nothing to sign in to; the header says so.
            if user or not settings.auth_required:
                return redirect("/"), "redirect"
            return login_page(search), "login"
        if user is None and settings.auth_required:
            return redirect(login_target(path, search)), "redirect"
        if current == "app":
            return no_update, no_update
        return app_shell(settings.auth_required), "app"

    dashboard.clientside_callback(
        """function(clicks, path, opened) {
          return window.dash_clientside.callback_context.triggered_id === "burger"
            ? !opened : false;
        }""",
        Output("mobile-navigation", "opened"),
        Input("burger", "n_clicks"),
        Input("url", "pathname"),
        State("mobile-navigation", "opened"),
        prevent_initial_call=True,
    )
    # Pure presentation stays in the browser: no HTTP request or session SQL read.
    # The drawer still owns focus trapping, Escape, backdrop and focus return.
    dashboard.clientside_callback(
        'function(opened) { return opened ? "true" : "false"; }',
        Output("burger", "aria-expanded"),
        Input("mobile-navigation", "opened"),
    )

    dashboard.clientside_callback(
        """function(path) {
          return (path || "").replace(/\\/$/, "") === "/administracion"
            ? {display: "none"} : {};
        }""",
        Output("data-status", "style"),
        Input("url", "pathname"),
    )
    # Presentation only: the sidebar repeats the origin already validated by `parse_context`,
    # read from the same query parameter, with no read of its own.
    dashboard.clientside_callback(
        """function(search) {
          const mode = new URLSearchParams(search || "").get("mode") || "fixture";
          if (mode === "fixture") { return "Muestra documental"; }
          return mode === "live" ? "Sandbox sintético" : "Origen no válido";
        }""",
        Output("navbar-origin", "children"),
        Input("url", "search"),
    )

    @dashboard.callback(
        Output(SEARCH_PATTERN, "value"),
        Input("url", "search"),
        State("url", "pathname"),
        State(SEARCH_PATTERN, "id"),
    )
    def sync_controls(search, path, searches):
        unchanged = [no_update] * len(searches)
        # A search change that leaves a list page also unmounts the bar; do not write to it.
        if not searchable(path):
            return unchanged
        try:
            context = parse_context(search)
        except ValueError:
            return unchanged
        return [context.query] * len(searches)

    @dashboard.callback(
        Output("url", "search"),
        Input(APPLY_PATTERN, "n_clicks"),
        Input(SEARCH_PATTERN, "n_submit"),
        Input({"type": "filter-tabs", "page": ALL}, "value"),
        State(SEARCH_PATTERN, "value"),
        State("url", "search"),
        prevent_initial_call=True,
    )
    def apply_query(clicks, submits, tabs, queries, search):
        trigger = ctx.triggered_id
        if not isinstance(trigger, dict):
            return no_update
        # The read callback validates these values again before accessing the service.
        try:
            current = parse_context(search)
        except ValueError:
            current = QueryContext()
        if trigger.get("type") == "filter-tabs":
            selected_filter = next((value for value in tabs if value), None)
            if not selected_filter or selected_filter == current.filter:
                return no_update
            params = {"mode": current.mode, "q": current.query, "filter": selected_filter}
        else:
            # Wildcard callbacks re-run when the bar mounts; only a click or Enter applies.
            if not any(clicks or []) and not any(submits or []):
                return no_update
            params = {
                "mode": current.mode,
                "q": (next(iter(queries), "") or "").strip(),
                "filter": current.filter,
            }
        if params["filter"] == "all":
            del params["filter"]
        return "?" + urlencode(params)

    dashboard.clientside_callback(
        STATUS_JS,
        Output("status", "data"),
        Output("registry", "data"),
        Input("status-poll", "n_intervals"),
        State("url", "search"),
        State("snapshot", "data"),
        State("workflow-snapshot", "data"),
        State("hub-loading", "data"),
        State("workflow-loading", "data"),
    )
    dashboard.clientside_callback(
        "function(hub, workflow) { return hub || workflow ? 'Actualizando…' : ''; }",
        Output("refresh-indicator", "children"),
        Input("hub-loading", "data"),
        Input("workflow-loading", "data"),
    )
    dashboard.clientside_callback(
        REREAD_JS,
        Output("registry", "data", allow_duplicate=True),
        Input("refresh", "n_clicks"),
        State("url", "search"),
        prevent_initial_call=True,
    )
    dashboard.clientside_callback(
        HEADER_JS
        % (
            json.dumps(FAMILY_COLORS),
            STATUS_POLL_SECONDS,
            STATUS_POLL_SECONDS,
        ),
        Output("read-status-text", "children"),
        Output("read-status-short", "children"),
        Output("read-status-dot", "style"),
        Output("registry-line", "children"),
        Output("sync-line", "children"),
        Output("poll-line", "children"),
        Input("status-poll", "n_intervals"),
        Input("snapshot", "data"),
        Input("status", "data"),
        Input("url", "pathname"),
        State("url", "search"),
    )

    def registry_version(mode: str) -> str | None:
        """Version taken before a read, so a change during the read still shows as stale."""
        try:
            return server.state.workflow.registry_state(mode).version
        except Exception:
            return None

    def stale_registry(registry, mode: str) -> bool:
        """A poll writes `registry` only when a store of this mode carries another version;
        the accessible fallback writes it with `forced`. Another mode's poll is ignored."""
        return isinstance(registry, dict) and registry.get("mode") == mode

    @dashboard.callback(
        Output("snapshot", "data"),
        Input("url", "search"),
        Input("registry", "data"),
        Input("url", "pathname"),
        Input("workflow-action-result", "data"),
        State("snapshot", "data"),
        running=[(Output("hub-loading", "data"), True, False)],
    )
    async def load_snapshot(search, registry, path, action, previous):
        if anonymous():
            return no_update
        normalized = (path or "/").rstrip("/") or "/"
        if (
            normalized == "/administracion"
            or normalized == "/operaciones"
            or normalized.startswith("/operaciones/")
        ):
            return no_update
        if ctx.triggered_id == "workflow-action-result" and (
            not isinstance(action, dict) or not action.get("ok")
        ):
            return no_update
        try:
            context = parse_context(search).for_read(path)
        except ValueError as error:
            return {"error": str(error), "key": None, "hub": None}
        # Changing a display filter needs no new provider read. Each browser owns its store.
        if (
            ctx.triggered_id == "url"
            and isinstance(previous, dict)
            and previous.get("key") == context.read_key
            and previous.get("hub") is not None
        ):
            return no_update
        if ctx.triggered_id == "registry" and (
            not stale_registry(registry, context.mode)
            or (
                not registry.get("forced")
                and isinstance(previous, dict)
                and previous.get("key") == context.read_key
                and previous.get("version") == registry.get("version")
            )
        ):
            return no_update
        result = {"key": context.read_key, "mode": context.mode}
        result["version"] = await run_in_threadpool(registry_version, context.mode)
        try:
            hub = await run_in_threadpool(
                read_hub,
                server.state.settings,
                server.state.nexus,
                context.mode,
                context.query,
                engine=server.state.engine,
                startrack=server.state.startrack,
            )
        except Exception:
            # Never return exceptions, upstream bodies, credentials or the previous success.
            return {**result, "hub": None, "error": READ_ERROR}
        return {**result, "hub": hub.model_dump(mode="json"), "error": None}

    @dashboard.callback(
        Output("workflow-snapshot", "data"),
        Input("url", "search"),
        Input("registry", "data"),
        Input("workflow-action-result", "data"),
        Input("url", "pathname"),
        State("workflow-snapshot", "data"),
        running=[(Output("workflow-loading", "data"), True, False)],
    )
    async def load_workflow(search, registry, action, path, previous):
        if anonymous() or (path or "").rstrip("/") == "/administracion":
            return no_update
        if (
            ctx.triggered_id == "workflow-action-result"
            and isinstance(action, dict)
            and not action.get("ok")
        ):
            # Keep operator inputs in place so a validation error can be corrected.
            return no_update
        try:
            context = parse_context(search)
        except ValueError:
            return {"mode": None, "overview": None}
        if (
            ctx.triggered_id == "url"
            and isinstance(previous, dict)
            and previous.get("mode") == context.mode
            and previous.get("overview") is not None
        ):
            return no_update
        if ctx.triggered_id == "registry" and (
            not stale_registry(registry, context.mode)
            or (
                not registry.get("forced")
                and isinstance(previous, dict)
                and previous.get("mode") == context.mode
                and previous.get("version") == registry.get("version")
            )
        ):
            return no_update
        result = {"mode": context.mode}
        result["version"] = await run_in_threadpool(registry_version, context.mode)
        try:
            overview = await run_in_threadpool(server.state.workflow.read, context.mode)
        except Exception:
            return {
                **result,
                "overview": None,
                "error": WORKFLOW_READ_ERROR,
            }
        return {**result, "overview": overview.model_dump(mode="json")}

    @dashboard.callback(
        Output("workflow-action-result", "data"),
        Input({"type": "workflow-action", "action": ALL, "movement": ALL}, "n_clicks"),
        State({"type": "workflow-field", "field": ALL}, "value"),
        State({"type": "workflow-field", "field": ALL}, "id"),
        State("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    async def act_on_workflow(clicks, values, identifiers, search, path):
        trigger = ctx.triggered_id
        if anonymous() or not isinstance(trigger, dict) or not any(clicks):
            return no_update
        result = {"token": str(uuid4()), "path": path, "search": search}
        try:
            context = parse_context(search)
            fields = {
                identifier["field"]: value
                for identifier, value in zip(identifiers, values, strict=True)
            }
            message, record = await run_in_threadpool(
                execute_action,
                server.state.workflow,
                trigger.get("action"),
                context.mode,
                fields,
                trigger.get("movement", ""),
            )
            result.update({"ok": True, "message": message})
            if record is not None:
                result["href"] = context.movement_href(record.id)
        except (WorkflowError, WorkflowInputError) as error:
            result.update({"ok": False, "message": str(error)})
        except (ValidationError, ValueError, TypeError, KeyError):
            result.update({"ok": False, "message": INPUT_ERROR})
        except Exception:
            result.update({"ok": False, "message": ACTION_ERROR})
        return result

    @dashboard.callback(
        Output("workflow-feedback", "children"),
        Input("workflow-action-result", "data"),
        Input("url", "pathname"),
        Input("url", "search"),
    )
    def action_feedback(result, path, search):
        if (
            not isinstance(result, dict)
            or result.get("path") != path
            or result.get("search") != search
        ):
            return None
        ok = bool(result.get("ok"))
        return notice(
            "Acción registrada" if ok else "Acción no completada",
            result.get("message", ""),
            error=not ok,
            children=[link("Abrir movimiento", result["href"], mt="xs")]
            if ok and result.get("href")
            else None,
        )

    @dashboard.callback(
        Output("content", "children"),
        Output("navigation", "children"),
        Output("mobile-navigation-links", "children"),
        Output("scope", "children"),
        Input("url", "pathname"),
        Input("url", "search"),
        Input("snapshot", "data"),
        Input("workflow-snapshot", "data"),
    )
    def render(path, search, snapshot, workflow_snapshot):
        path = (path or "/").rstrip("/") or "/"
        if anonymous():
            return redirect(login_target(path, search)), None, None, None
        try:
            context = parse_context(search)
        except ValueError as error:
            nav = navigation(path, QueryContext())
            return notice("Consulta inválida", str(error), error=True), nav, nav, None
        nav = navigation(path, context)
        if path == "/administracion":
            return admin_page(), nav, nav, None
        workflow = workflow_from(workflow_snapshot, context.mode)
        # Persisted evidence stays readable when the current provider read is unavailable.
        if path == "/operaciones" or path.startswith("/operaciones/"):
            line = origin_line(context, path)
            return (
                list_controls(workflow_page(path, workflow, context), path, context),
                nav,
                nav,
                line,
            )
        if path in {"/", "/resumen", "/decisiones", "/indicadores", "/integracion", "/fuentes"}:
            context = QueryContext(mode=context.mode)
        read_context = context.for_read(path)
        if not isinstance(snapshot, dict) or snapshot.get("key") != read_context.read_key:
            return loading(), nav, nav, None
        if snapshot.get("error"):
            return notice("Consulta no disponible", snapshot["error"], error=True), nav, nav, None
        try:
            hub = HubResponse.model_validate(snapshot.get("hub"))
            if hub.mode != context.mode or hub.scope.search != read_context.query:
                raise ValueError("La respuesta no corresponde a esta consulta.")
        except (ValidationError, ValueError):
            message = "Actualiza la consulta para recuperar los datos."
            return notice("Respuesta no válida", message, error=True), nav, nav, None
        page = list_controls(render_page(path, hub, context, workflow), path, context)
        page_scope = scope(hub, context, workflow, path)
        return page, nav, nav, page_scope

    @dashboard.callback(
        Output(PANEL_PATTERN, "children"),
        Input(SELECT_PATTERN, "value"),
        State("snapshot", "data"),
        State("workflow-snapshot", "data"),
        State("url", "search"),
        State("url", "pathname"),
        prevent_initial_call=True,
    )
    def show_trace(selected, snapshot, workflow_snapshot, search, path):
        """Change the followed request without a new provider read; the store already has it."""
        request_id = next((value for value in selected if value), None)
        if anonymous() or request_id is None:
            return [no_update] * len(selected)
        try:
            context = parse_context(search)
            read_context = context.for_read(path)
        except ValueError:
            return [no_update] * len(selected)
        if not isinstance(snapshot, dict) or snapshot.get("key") != read_context.read_key:
            return [loading()] * len(selected)
        try:
            hub = HubResponse.model_validate(snapshot.get("hub"))
        except (ValidationError, ValueError):
            return [no_update] * len(selected)
        workflow = workflow_from(workflow_snapshot, context.mode)
        return [trace_panel(hub, context, workflow, request_id) for _ in selected]

    return dashboard

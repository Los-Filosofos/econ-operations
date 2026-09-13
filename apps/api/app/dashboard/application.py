"""Dash on the existing FastAPI server, using the shared Python read service."""

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
from app.dashboard.theme import BRAND, MANTINE_THEME
from app.dashboard.views import (
    MODES,
    REQUEST_FILTERS,
    filter_tabs,
    navigation,
    render_page,
    scope,
    workflow_page,
)
from app.dashboard.workflow_actions import WorkflowInputError, execute_action
from app.dashboard.workflow_forms import action_button, plan_form, receipt_form
from app.models.hub import HubResponse
from app.models.workflow import WorkflowOverview
from app.services.hub import read_hub
from app.services.workflow import WorkflowError

ASSETS = Path(__file__).parent / "assets"
STYLESHEET_VERSION = sha256((ASSETS / "style.css").read_bytes()).hexdigest()[:12]
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
READ_ERROR = "No se pudo completar la consulta. Intenta actualizar de nuevo."
INPUT_ERROR = (
    "Revisa los campos obligatorios y los IDs. Usa fecha AAAA-MM-DD y hora HH:MM; "
    "separa los IDs de usuarios con comas."
)
ACTION_ERROR = (
    "No se pudo completar la acción. Actualiza el registro para consultar su estado "
    "antes de repetirla."
)


def query_controls():
    return dmc.Group(
        [
            dmc.TextInput(
                id="search",
                label="Buscar",
                value="",
                placeholder="Proyecto, solicitud o maquinaria…",
                leftSection=icon("search", 16),
                autoComplete="off",
                style={"flex": 1, "minWidth": 220},
            ),
            dmc.Select(
                id="mode",
                label="Origen de datos",
                value="fixture",
                data=[{"value": value, "label": label} for value, label in MODES.items()],
                allowDeselect=False,
                w={"base": "100%", "xs": 240},
            ),
            dmc.Button("Aplicar", id="apply", n_clicks=0, style={"alignSelf": "flex-end"}),
        ],
        align="flex-end",
        gap="sm",
        className="query-bar",
    )


def brand(height=34):
    return dmc.Anchor(
        html.Img(src="/assets/econ-color.png", alt="Grupo ECON", height=height),
        href="/",
        **{"aria-label": "Inicio"},
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
                brand(),
                dmc.Text("Control de maquinaria", size="sm", c="dimmed", visibleFrom="xs"),
                dmc.Group(
                    [
                        html.Div(header_user(current_user(), auth_required), id="header-user"),
                        dmc.Button(
                            dmc.Text("Actualizar", span=True, size="sm", visibleFrom="xs"),
                            id="refresh",
                            n_clicks=0,
                            variant="default",
                            size="sm",
                            leftSection=icon("refresh", 16),
                            **{"aria-label": "Actualizar"},
                        ),
                    ],
                    gap="xs",
                    ml="auto",
                    wrap="nowrap",
                ),
            ],
            h="100%",
            px="md",
            gap="md",
            wrap="nowrap",
        )
    )
    navbar = dmc.AppShellNavbar(
        html.Nav(id="navigation", **{"aria-label": "Navegación principal"}), p="sm"
    )
    stores = [
        dcc.Store(id="snapshot", storage_type="memory"),
        dcc.Store(id="workflow-snapshot", storage_type="memory"),
        dcc.Store(id="workflow-action-result", storage_type="memory"),
    ]
    main = dmc.AppShellMain(
        dmc.Container(
            [
                query_controls(),
                html.Div(id="scope"),
                html.Div(id="workflow-feedback", **{"aria-live": "polite"}),
                dcc.Loading(
                    [*stores, html.Main(id="content", tabIndex=-1)],
                    custom_spinner=dmc.Loader(color=BRAND, size="md"),
                    target_components={
                        "snapshot": "data",
                        "workflow-snapshot": "data",
                        "workflow-action-result": "data",
                        "content": "children",
                    },
                    delay_show=150,
                    overlay_style={"visibility": "hidden"},
                ),
            ],
            size=1400,
            px=0,
        )
    )
    return html.Div(
        [
            html.A("Saltar al contenido", href="#content", className="skip-link"),
            dmc.AppShell(
                [header, navbar, main],
                header={"height": 60},
                navbar={"width": 236, "breakpoint": "sm", "collapsed": {"mobile": True}},
                padding="md",
            ),
            dmc.Drawer(
                html.Nav(id="mobile-navigation-links", **{"aria-label": "Navegación principal"}),
                id="mobile-navigation",
                title=brand(30),
                opened=False,
                size=280,
                padding="md",
                closeButtonProps={"aria-label": "Cerrar navegación"},
            ),
        ]
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
            # The signed-in header only exists inside a request; declare its IDs here.
            dmc.MenuItem("Cerrar sesión", id="logout", n_clicks=0),
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
        assets_ignore=r"style\.css",
        external_stylesheets=[f"/assets/style.css?v={STYLESHEET_VERSION}"],
        title="ECON · Seguimiento de solicitudes",
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
            return (redirect("/"), "redirect") if user else (login_page(search), "login")
        if user is None and settings.auth_required:
            return redirect(login_target(path, search)), "redirect"
        if current == "app":
            return no_update, no_update
        return app_shell(settings.auth_required), "app"

    @dashboard.callback(
        Output("mobile-navigation", "opened"),
        Input("burger", "n_clicks"),
        Input("url", "pathname"),
        State("mobile-navigation", "opened"),
        prevent_initial_call=True,
    )
    def toggle_navigation(_clicks, _path, opened):
        # The drawer owns focus trapping, Escape, backdrop and focus return.
        return not opened if ctx.triggered_id == "burger" else False

    @dashboard.callback(Output("burger", "aria-expanded"), Input("mobile-navigation", "opened"))
    def sync_burger(opened):
        return "true" if opened else "false"

    @dashboard.callback(
        Output("mode", "value"),
        Output("search", "value"),
        Input("url", "search"),
    )
    def sync_controls(search):
        try:
            context = parse_context(search)
        except ValueError:
            return no_update, no_update
        return context.mode, context.query

    @dashboard.callback(
        Output("url", "search"),
        Input("apply", "n_clicks"),
        Input("search", "n_submit"),
        Input({"type": "filter-tabs", "page": ALL}, "value"),
        State("mode", "value"),
        State("search", "value"),
        State("url", "search"),
        prevent_initial_call=True,
    )
    def apply_query(clicks, submit, tabs, mode, query, search):
        # Wildcard callbacks re-run when the shell mounts; only a real click or Enter applies.
        if not isinstance(ctx.triggered_id, dict) and not (clicks or submit):
            return no_update
        # The read callback validates these values again before accessing the service.
        try:
            current = parse_context(search)
        except ValueError:
            current = QueryContext()
        if isinstance(ctx.triggered_id, dict):
            selected_filter = next((value for value in tabs if value), None)
            if not selected_filter or selected_filter == current.filter:
                return no_update
            params = {"mode": current.mode, "q": current.query, "filter": selected_filter}
        else:
            params = {"mode": mode or "", "q": (query or "").strip(), "filter": current.filter}
        if params["filter"] == "all":
            del params["filter"]
        return "?" + urlencode(params)

    @dashboard.callback(
        Output("snapshot", "data"),
        Input("url", "search"),
        Input("refresh", "n_clicks"),
        Input("url", "pathname"),
        Input("workflow-action-result", "data"),
        State("snapshot", "data"),
    )
    async def load_snapshot(search, _refresh, path, action, previous):
        if anonymous():
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
            return {"key": context.read_key, "hub": None, "error": READ_ERROR}
        return {"key": context.read_key, "hub": hub.model_dump(mode="json"), "error": None}

    @dashboard.callback(
        Output("workflow-snapshot", "data"),
        Input("url", "search"),
        Input("refresh", "n_clicks"),
        Input("workflow-action-result", "data"),
    )
    async def load_workflow(search, _refresh, action):
        if anonymous():
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
        try:
            overview = await run_in_threadpool(server.state.workflow.read, context.mode)
        except Exception:
            return {
                "mode": context.mode,
                "overview": None,
                "error": "No se pudo consultar el registro de movimientos. Intenta actualizar.",
            }
        return {"mode": context.mode, "overview": overview.model_dump(mode="json")}

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
            mode = dmc.Text(MODES[context.mode], size="xs", fw=500, className="scope-line")
            return workflow_page(path, workflow, context), nav, nav, mode
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
        page = render_page(path, hub, context, workflow)
        return page, nav, nav, scope(hub, context, workflow)

    return dashboard

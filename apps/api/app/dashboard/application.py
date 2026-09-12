"""Dash on the existing FastAPI server, using the shared Python read service."""

from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from dash import ALL, Dash, Input, Output, State, ctx, dcc, html, no_update
from fastapi import FastAPI
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.dashboard.context import QueryContext, parse_context
from app.dashboard.views import empty, navigation, notice, render_page, scope
from app.dashboard.workflow_actions import execute_action
from app.dashboard.workflow_forms import validation_controls
from app.dashboard.workflow_views import workflow_page
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


def query_controls():
    return html.Div(
        [
            html.Div(
                [
                    html.Label("Buscar", htmlFor="search"),
                    dcc.Input(
                        id="search",
                        type="search",
                        value="",
                        maxLength=100,
                        placeholder="Proyecto, solicitud o maquinaria…",
                        autoComplete="off",
                    ),
                ],
                className="search-control",
            ),
            html.Div(
                [
                    html.Label("Origen de datos", htmlFor="mode"),
                    dcc.Dropdown(
                        id="mode",
                        value="fixture",
                        clearable=False,
                        searchable=False,
                        options=[
                            {"label": "Muestras proporcionadas", "value": "fixture"},
                            {"label": "Sandbox actual (sintético)", "value": "live"},
                        ],
                    ),
                ],
                className="source-control",
            ),
            html.Button("Aplicar", id="apply", n_clicks=0, className="button primary"),
        ],
        className="query-bar",
    )


def layout():
    return html.Div(
        [
            dcc.Location(id="url", refresh="callback-nav"),
            dcc.Store(id="navigation-focus", storage_type="memory"),
            html.A("Saltar al contenido", href="#content", className="skip-link"),
            html.Div(
                [
                    html.Aside(
                        [
                            html.Div(
                                [
                                    html.Button(
                                        "Cerrar",
                                        id="sidebar-close",
                                        n_clicks=0,
                                        className="button sidebar-close",
                                        type="button",
                                        **{"aria-label": "Cerrar navegación lateral"},
                                    ),
                                    dcc.Link(
                                        html.Img(src="/assets/econ-color.png", alt="Grupo ECON"),
                                        href="/",
                                        className="brand",
                                    ),
                                    html.P("Control de maquinaria", className="brand-caption"),
                                ],
                                className="sidebar-brand",
                            ),
                            html.Span("Espacio de trabajo", className="nav-heading"),
                            html.Nav(id="navigation", **{"aria-label": "Navegación principal"}),
                            html.Div(
                                [
                                    html.Span("Entorno del proyecto"),
                                    html.Strong("Datos sintéticos"),
                                ],
                                className="sidebar-footer",
                            ),
                        ],
                        id="sidebar",
                        className="sidebar",
                    ),
                    html.Button(
                        id="sidebar-dismiss",
                        n_clicks=0,
                        className="sidebar-backdrop",
                        type="button",
                        **{"aria-label": "Cerrar navegación", "tabIndex": -1},
                    ),
                    html.Div(
                        [
                            html.Header(
                                [
                                    html.Button(
                                        [
                                            html.Span(
                                                className="menu-lines", **{"aria-hidden": True}
                                            ),
                                            "Menú",
                                        ],
                                        id="sidebar-toggle",
                                        n_clicks=0,
                                        className="button menu-toggle",
                                        type="button",
                                        **{"aria-controls": "sidebar", "aria-expanded": "false"},
                                    ),
                                    html.Span(
                                        "Operación de maquinaria", className="workspace-title"
                                    ),
                                    html.Button(
                                        "Actualizar datos",
                                        id="refresh",
                                        n_clicks=0,
                                        className="button refresh-button",
                                    ),
                                ],
                                className="workspace-bar",
                            ),
                            html.Div(
                                [
                                    query_controls(),
                                    dcc.Loading(
                                        [
                                            dcc.Store(id="snapshot", storage_type="memory"),
                                            dcc.Store(
                                                id="workflow-snapshot", storage_type="memory"
                                            ),
                                            dcc.Store(
                                                id="workflow-action-result", storage_type="memory"
                                            ),
                                            html.Div(id="scope"),
                                            html.Div(
                                                id="workflow-feedback", **{"aria-live": "polite"}
                                            ),
                                            html.Main(id="content", tabIndex=-1),
                                        ],
                                        target_components={
                                            "snapshot": "data",
                                            "workflow-snapshot": "data",
                                            "workflow-action-result": "data",
                                            "content": "children",
                                        },
                                        type="circle",
                                        color="#144f81",
                                        delay_show=150,
                                        overlay_style={"visibility": "hidden"},
                                    ),
                                ],
                                className="workspace-content",
                            ),
                        ],
                        className="workspace",
                    ),
                ],
                className="app-body",
            ),
        ],
        id="app-shell",
        className="app",
    )


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
    dashboard.layout = layout
    dashboard.validation_layout = html.Div([layout(), validation_controls()])

    @dashboard.callback(
        Output("app-shell", "className"),
        Output("sidebar-toggle", "aria-expanded"),
        Input("sidebar-toggle", "n_clicks"),
        Input("sidebar-dismiss", "n_clicks"),
        Input("sidebar-close", "n_clicks"),
        Input("url", "pathname"),
        State("app-shell", "className"),
        prevent_initial_call=True,
    )
    def toggle_navigation(_toggle, _dismiss, _close, _path, current_class):
        opened = ctx.triggered_id == "sidebar-toggle" and "nav-open" not in (current_class or "")
        return ("app nav-open", "true") if opened else ("app", "false")

    dashboard.clientside_callback(
        """function(classes) {
            const panel = document.getElementById('sidebar');
            const opened = (classes || '').includes('nav-open');
            const mobile = window.matchMedia('(max-width: 980px)').matches;
            if (panel) {
                panel.onkeydown = function(event) {
                    if (!opened || !mobile) return;
                    if (event.key === 'Escape') {
                        event.preventDefault();
                        document.getElementById('sidebar-close').click();
                    } else if (event.key === 'Tab') {
                        const targets = panel.querySelectorAll('a[href], button');
                        const first = targets[0];
                        const last = targets[targets.length - 1];
                        if (event.shiftKey && document.activeElement === first) {
                            event.preventDefault();
                            last.focus();
                        } else if (!event.shiftKey && document.activeElement === last) {
                            event.preventDefault();
                            first.focus();
                        }
                    }
                };
            }
            if (mobile) {
                // Wait for Dash's DOM commit and the drawer's visibility transition.
                window.setTimeout(function() {
                    const shell = document.getElementById('app-shell');
                    if (!shell || shell.classList.contains('nav-open') !== opened) return;
                    const id = opened ? 'sidebar-close' : 'sidebar-toggle';
                    const target = document.getElementById(id);
                    if (target) target.focus();
                }, 200);
            }
            return opened;
        }""",
        Output("navigation-focus", "data"),
        Input("app-shell", "className"),
        prevent_initial_call=True,
    )

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
        State("mode", "value"),
        State("search", "value"),
        prevent_initial_call=True,
    )
    def apply_query(_clicks, _submit, mode, query):
        # The read callback validates these values again before accessing the service.
        return "?" + urlencode({"mode": mode or "", "q": (query or "").strip()})

    @dashboard.callback(
        Output("snapshot", "data"),
        Input("url", "search"),
        Input("refresh", "n_clicks"),
        State("snapshot", "data"),
    )
    async def load_snapshot(search, _refresh, previous):
        try:
            context = parse_context(search)
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
            )
        except Exception:
            # Never return exceptions, upstream bodies, credentials or the previous success.
            return {
                "key": context.read_key,
                "hub": None,
                "error": "No se pudo completar la consulta. Intenta actualizar de nuevo.",
            }
        return {"key": context.read_key, "hub": hub.model_dump(mode="json"), "error": None}

    @dashboard.callback(
        Output("workflow-snapshot", "data"),
        Input("url", "search"),
        Input("refresh", "n_clicks"),
        Input("workflow-action-result", "data"),
    )
    async def load_workflow(search, _refresh, _action):
        if (
            ctx.triggered_id == "workflow-action-result"
            and isinstance(_action, dict)
            and not _action.get("ok")
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
        if not isinstance(trigger, dict) or not any(clicks):
            return no_update
        result = {"token": str(uuid4()), "path": path, "search": search}
        try:
            context = parse_context(search)
            fields = {
                identifier["field"]: value
                for identifier, value in zip(identifiers, values, strict=True)
            }
            action = trigger.get("action")
            movement = trigger.get("movement", "")
            message, record = await run_in_threadpool(
                execute_action, server.state.workflow, action, context.mode, fields, movement
            )
            result.update({"ok": True, "message": message})
            if record is not None:
                result["href"] = context.movement_href(record.id)
        except WorkflowError as error:
            result.update({"ok": False, "message": str(error)})
        except (ValidationError, ValueError, TypeError, KeyError):
            result.update(
                {
                    "ok": False,
                    "message": "Revisa los campos obligatorios y los IDs. Usa fecha AAAA-MM-DD "
                    "y hora HH:MM; separa los IDs de usuarios con comas.",
                }
            )
        except Exception:
            result.update(
                {
                    "ok": False,
                    "message": "No se pudo completar la acción. Actualiza el registro para "
                    "consultar su estado antes de repetirla.",
                }
            )
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
        children = [
            notice(
                "Acción registrada" if result.get("ok") else "Acción no completada",
                result.get("message", ""),
                error=not result.get("ok"),
            )
        ]
        if result.get("ok") and result.get("href"):
            children.append(dcc.Link("Abrir movimiento", href=result["href"]))
        return children

    @dashboard.callback(
        Output("content", "children"),
        Output("navigation", "children"),
        Output("scope", "children"),
        Input("url", "pathname"),
        Input("url", "search"),
        Input("snapshot", "data"),
        Input("workflow-snapshot", "data"),
    )
    def render(path, search, snapshot, workflow_snapshot):
        path = (path or "/").rstrip("/") or "/"
        try:
            context = parse_context(search)
        except ValueError as error:
            return (
                notice("Consulta inválida", str(error), error=True),
                navigation(path, QueryContext()),
                None,
            )
        nav = navigation(path, context)
        workflow = None
        if isinstance(workflow_snapshot, dict) and workflow_snapshot.get("mode") == context.mode:
            try:
                workflow = WorkflowOverview.model_validate(workflow_snapshot.get("overview"))
                if any(movement.mode != context.mode for movement in workflow.movements):
                    raise ValueError("Los movimientos no corresponden al origen seleccionado.")
            except (ValidationError, ValueError):
                workflow = None
                if workflow_snapshot.get("error"):
                    workflow = WorkflowOverview(
                        available=False,
                        message=workflow_snapshot["error"],
                        management_enabled=False,
                        sending_enabled=False,
                        movements=[],
                        last_sync_at=None,
                    )
        # Persisted evidence stays readable when the current provider read is unavailable.
        if path == "/operaciones" or path.startswith("/operaciones/"):
            return (
                workflow_page(path, workflow, context),
                nav,
                html.Div(
                    "Muestras proporcionadas"
                    if context.mode == "fixture"
                    else "Sandbox actual (sintético)",
                    className="scope-line",
                ),
            )
        if not isinstance(snapshot, dict) or snapshot.get("key") != context.read_key:
            return (
                empty("Consultando la operación…", "Preparando los datos del origen seleccionado."),
                nav,
                None,
            )
        if snapshot.get("error"):
            return notice("Consulta no disponible", snapshot["error"], error=True), nav, None
        try:
            hub = HubResponse.model_validate(snapshot.get("hub"))
            if hub.mode != context.mode or hub.scope.search != context.query:
                raise ValueError("La respuesta no corresponde a esta consulta.")
        except (ValidationError, ValueError):
            return (
                notice(
                    "Respuesta no válida",
                    "Actualiza la consulta para recuperar los datos.",
                    error=True,
                ),
                nav,
                None,
            )
        return render_page(path, hub, context, workflow), nav, scope(hub, context, workflow)

    return dashboard

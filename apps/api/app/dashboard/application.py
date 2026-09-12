"""Dash on the existing FastAPI server, using the shared Python read service."""

from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode

from dash import Dash, Input, Output, State, ctx, dcc, html, no_update
from fastapi import FastAPI
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.dashboard.context import QueryContext, parse_context
from app.dashboard.views import empty, navigation, notice, render_page, scope
from app.models.hub import HubResponse
from app.services.hub import read_hub

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


def layout():
    return html.Div(
        [
            dcc.Location(id="url", refresh="callback-nav"),
            html.A("Saltar al contenido", href="#content", className="skip-link"),
            html.Header(
                [
                    dcc.Link(
                        html.Img(src="/assets/econ-color.png", alt="Grupo ECON"),
                        href="/",
                        className="brand",
                    ),
                    html.Div(
                        [
                            html.Strong("Hub de operaciones"),
                            html.Span("Maquinaria · Logística · Proyectos"),
                        ],
                        className="brand-caption",
                    ),
                ],
                className="app-header",
            ),
            html.Div(
                [
                    html.Aside(
                        [
                            html.Span("OPERACIÓN", className="nav-label"),
                            html.Nav(id="navigation", **{"aria-label": "Navegación principal"}),
                            html.P("Información conectada para decidir.", className="sidebar-note"),
                        ],
                        className="sidebar",
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Label("Origen de datos", htmlFor="mode"),
                                            dcc.Dropdown(
                                                id="mode",
                                                value="fixture",
                                                clearable=False,
                                                searchable=False,
                                                options=[
                                                    {
                                                        "label": "Ejemplos locales",
                                                        "value": "fixture",
                                                    },
                                                    {"label": "Sandbox en vivo", "value": "live"},
                                                ],
                                            ),
                                        ],
                                        className="source-control",
                                    ),
                                    html.Div(
                                        [
                                            html.Label(
                                                "Buscar equipo, proyecto o solicitud",
                                                htmlFor="search",
                                            ),
                                            dcc.Input(
                                                id="search",
                                                type="search",
                                                value="",
                                                maxLength=100,
                                                placeholder="Código, proyecto o solicitud…",
                                                autoComplete="off",
                                            ),
                                        ],
                                        className="search-control",
                                    ),
                                    html.Button(
                                        "Aplicar",
                                        id="apply",
                                        n_clicks=0,
                                        className="button primary",
                                    ),
                                    html.Button(
                                        "Actualizar", id="refresh", n_clicks=0, className="button"
                                    ),
                                ],
                                className="query-bar",
                            ),
                            dcc.Loading(
                                [
                                    dcc.Store(id="snapshot", storage_type="memory"),
                                    html.Div(id="scope"),
                                    html.Main(id="content", tabIndex=-1),
                                ],
                                target_components={"snapshot": "data", "content": "children"},
                                type="circle",
                                color="#144f81",
                                delay_show=150,
                                overlay_style={"visibility": "hidden"},
                            ),
                        ],
                        className="workspace",
                    ),
                ],
                className="app-body",
            ),
        ],
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
        title="ECON · Hub de operaciones",
        update_title="Consultando…",
        index_string=INDEX,
        suppress_callback_exceptions=False,
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    )
    dashboard.layout = layout

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
        Output("content", "children"),
        Output("navigation", "children"),
        Output("scope", "children"),
        Input("url", "pathname"),
        Input("url", "search"),
        Input("snapshot", "data"),
    )
    def render(path, search, snapshot):
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
        return render_page(path, hub, context), nav, scope(hub)

    return dashboard

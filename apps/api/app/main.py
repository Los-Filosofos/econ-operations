from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from secrets import token_urlsafe

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse, Response

from app.api.auth import router as auth_router
from app.api.documentation import API_DESCRIPTION, OPENAPI_TAGS
from app.api.health import router as health_router
from app.api.hub import router as hub_router
from app.api.users import router as users_router
from app.api.workflow import router as workflow_router
from app.core.access import management_scope
from app.core.auth import SESSION_COOKIE, authorize_request
from app.core.config import Settings
from app.core.database import build_engine
from app.dashboard.application import create_dashboard
from app.integrations.nexus import NexusConnector
from app.integrations.startrack import StartrackClient, StartrackReadConfig
from app.services.workflow import WorkflowError, WorkflowService

AUTH_TAGS = [
    {
        "name": "Autenticación",
        "description": (
            "Sesión por cookie firmada HttpOnly (SameSite=Lax). Roles: admin, "
            "gerencia_proyecto, logistica, mantenimiento, control_costos y lectura. Permisos: "
            "read (todos), manage_transfers (logistica, admin), declare_reception "
            "(gerencia_proyecto, logistica, admin) y manage_users (admin). Sin sesión, "
            "/api/v1/* responde 401 y las páginas redirigen a /login; sin permiso, 403."
        ),
    },
    {"name": "Usuarios", "description": "Administración de usuarios y roles (solo admin)."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.engine = build_engine(settings.database_url)
        application.state.nexus = NexusConnector(settings)
        application.state.startrack = StartrackClient(
            StartrackReadConfig(
                enabled=settings.allow_live_reads,
                allow_writes=settings.allow_live_writes,
                api_key=settings.startrack_api_key,
                password=settings.startrack_password,
                page_size=settings.startrack_page_size,
                max_pages=settings.startrack_max_pages,
                timeout_seconds=settings.startrack_timeout_seconds,
                budget_seconds=settings.startrack_budget_seconds,
            )
        )
        application.state.workflow = WorkflowService(
            settings,
            application.state.engine,
            application.state.nexus,
            application.state.startrack,
        )
        try:
            yield
        finally:
            await run_in_threadpool(application.state.nexus.close)
            await run_in_threadpool(application.state.startrack.close)
            await run_in_threadpool(application.state.engine.dispose)

    application = FastAPI(
        title=settings.app_name,
        description=API_DESCRIPTION,
        openapi_tags=[*OPENAPI_TAGS, *AUTH_TAGS],
        swagger_ui_parameters={
            "displayRequestDuration": True,
            "filter": True,
            "defaultModelsExpandDepth": -1,
            "persistAuthorization": False,
        },
        version="0.2.0",
        lifespan=lifespan,
    )
    application.state.settings = settings

    @application.middleware("http")
    async def authorize(request: Request, call_next):
        decision = await run_in_threadpool(authorize_request, request, settings)
        if isinstance(decision, Response):
            return decision
        with management_scope(decision):
            response = await call_next(request)
        if request.url.path.startswith(("/_dash-", "/api/v1/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(WorkflowError)
    async def workflow_error(_request: Request, error: WorkflowError):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    # Added after the authorize middleware so the session is decoded before it runs.
    # Without AUTH_REQUIRED a missing secret only makes sessions process-local.
    application.add_middleware(
        SessionMiddleware,
        secret_key=(
            settings.session_secret.get_secret_value()
            if settings.session_secret
            else token_urlsafe(32)
        ),
        session_cookie=SESSION_COOKIE,
        max_age=settings.session_max_age_seconds,
        same_site="lax",
        https_only=settings.session_https_only,
    )
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(hub_router)
    application.include_router(workflow_router)
    application.state.dashboard = create_dashboard(application)
    return application


app = create_app()

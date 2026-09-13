from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app.api.documentation import API_DESCRIPTION, OPENAPI_TAGS
from app.api.health import router as health_router
from app.api.hub import router as hub_router
from app.api.workflow import router as workflow_router
from app.core.access import local_request, management_scope
from app.core.config import Settings
from app.core.database import build_engine
from app.dashboard.application import create_dashboard
from app.integrations.nexus import NexusConnector
from app.integrations.startrack import StartrackClient, StartrackReadConfig
from app.services.workflow import WorkflowError, WorkflowService


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
        openapi_tags=OPENAPI_TAGS,
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
    async def private_callback_responses(request: Request, call_next):
        with management_scope(settings.allow_local_management and local_request(request)):
            response = await call_next(request)
        if request.url.path.startswith(("/_dash-", "/api/v1/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(WorkflowError)
    async def workflow_error(_request: Request, error: WorkflowError):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.include_router(health_router)
    application.include_router(hub_router)
    application.include_router(workflow_router)
    application.state.dashboard = create_dashboard(application)
    return application


app = create_app()

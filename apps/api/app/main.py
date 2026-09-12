from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.api.health import router as health_router
from app.api.hub import router as hub_router
from app.core.config import Settings
from app.core.database import build_engine
from app.integrations.nexus import NexusConnector


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.engine = build_engine(settings.database_url)
        application.state.nexus = NexusConnector(settings)
        try:
            yield
        finally:
            await run_in_threadpool(application.state.nexus.close)
            await run_in_threadpool(application.state.engine.dispose)

    application = FastAPI(
        title=settings.app_name,
        description=(
            "Hub de consulta operativa. Separa ejemplos locales, lecturas del sandbox, "
            "estados originales y evidencia. No modifica las plataformas externas."
        ),
        version="0.2.0",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.include_router(health_router)
    application.include_router(hub_router)
    return application


app = create_app()

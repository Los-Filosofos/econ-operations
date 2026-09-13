from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.documentation import ErrorResponse
from app.core.database import SessionDep

router = APIRouter(prefix="/health", tags=["Salud"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


@router.get(
    "/live",
    summary="Comprobar que la API responde",
    description="Comprueba el proceso sin consultar SQL, migraciones, Prisma ni Startrack.",
)
def liveness() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/ready",
    summary="Comprobar conexión a la base de datos",
    description=(
        "Ejecuta SELECT 1. No acredita migraciones aplicadas ni conectividad a proveedores. "
        "El proceso puede seguir vivo aunque esta comprobación devuelva 503."
    ),
    responses={
        503: {
            "model": ErrorResponse,
            "description": "La conexión SQL no está disponible.",
            "content": {"application/json": {"example": {"detail": "Base de datos no disponible"}}},
        }
    },
)
def readiness(session: SessionDep) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Never expose connection strings or database exception details over HTTP.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from None
    return HealthResponse()

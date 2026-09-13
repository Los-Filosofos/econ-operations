"""Cheap registry version and synchronization state; the page polls it instead of a button."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from app.api.documentation import MODE_DESCRIPTION, ErrorResponse
from app.models.hub import DataMode
from app.services.workflow import SyncStatus

router = APIRouter(prefix="/api/v1", tags=["Estado"])


class StatusResponse(BaseModel):
    mode: DataMode
    registry_version: str = Field(
        description=(
            "Hash corto y determinista del registro del modo. Cambia solo cuando cambió lo "
            "guardado (planes, eventos, recepciones o un corte nuevo); una relectura sin "
            "cambios lo conserva. Compararlo con el valor anterior basta para saber si hay "
            "que volver a leer."
        )
    )
    registry_last_read_at: datetime | None = Field(
        description=(
            "Última lectura del origen guardada para el modo (fecha del último corte o de su "
            "confirmación sin cambios), por cualquier proceso; null si nunca se sincronizó."
        )
    )
    hub_data_as_of: datetime | None = Field(
        description="Corte del origen del último corte guardado; null sin corte o sin fecha."
    )
    sync: SyncStatus = Field(
        description=(
            "Sincronización automática de este proceso: enabled solo con SYNC_INTERVAL_SECONDS "
            "> 0 y ALLOW_LIVE_READS=true en live, nunca en fixture. last_cycle_* describen el "
            "último ciclo automático de este proceso; el worker CLI de otro proceso solo se "
            "refleja en registry_last_read_at."
        )
    )


@router.get(
    "/status",
    summary="Consultar la versión del registro y el estado de la sincronización",
    description=(
        "Lectura ligera sin llamadas a proveedores: dos consultas SQL sobre el registro del "
        "modo. La interfaz la sondea cada 15 s y vuelve a leer datos solo cuando "
        "registry_version cambia. Se sirve con Cache-Control: no-store y requiere la misma "
        "sesión que el resto de la API."
    ),
    responses={
        503: {
            "model": ErrorResponse,
            "description": "El registro SQL no está disponible.",
            "content": {"application/json": {"example": {"detail": "Registro no disponible"}}},
        }
    },
)
def read_status(
    request: Request,
    response: Response,
    mode: Annotated[DataMode, Query(description=MODE_DESCRIPTION)] = "fixture",
) -> StatusResponse:
    response.headers["Cache-Control"] = "no-store"
    workflow = request.app.state.workflow
    try:
        registry = workflow.registry_state(mode)
    except SQLAlchemyError:
        # Never expose connection strings or database exception details over HTTP.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Registro no disponible"
        ) from None
    return StatusResponse(
        mode=mode,
        registry_version=registry.version,
        registry_last_read_at=registry.last_read_at,
        hub_data_as_of=registry.data_as_of,
        sync=workflow.sync_status(mode),
    )

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.models.hub import DataMode, HubResponse
from app.services.hub import read_hub

router = APIRouter(prefix="/api/v1", tags=["Operations hub"])


@router.get("/hub", summary="Consultar maquinaria, solicitudes y evidencia por fuente")
def get_hub(
    request: Request,
    response: Response,
    mode: DataMode = "fixture",
    search: Annotated[str, Query(max_length=100)] = "",
) -> HubResponse:
    response.headers["Cache-Control"] = "no-store"
    return read_hub(request.app.state.settings, request.app.state.nexus, mode, search)

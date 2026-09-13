from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.api.documentation import MODE_DESCRIPTION
from app.models.hub import DataMode, HubResponse
from app.services.hub import read_hub

router = APIRouter(prefix="/api/v1", tags=["Consulta operativa"])


@router.get(
    "/hub",
    summary="Consultar maquinaria, solicitudes y evidencia por fuente",
    description=(
        "Proyección de lectura compartida con Dash. En live consulta páginas acotadas de Prisma; "
        "el seguimiento de Startrack procede del registro local, sin refrescar el proveedor. "
        "Revisar sources, scope.complete y operation_evidence: un 200 puede contener fuentes "
        "disabled, not_configured o error, registros vacíos y contadores null. "
        "Las cinco máquinas y dos solicitudes fixture no constituyen una flota completa. "
        "generated_at no es el instante de la evidencia; data_as_of puede ser null. "
        "Los totales de scope preceden al filtro; summary describe los registros devueltos."
    ),
)
def get_hub(
    request: Request,
    response: Response,
    mode: Annotated[DataMode, Query(description=MODE_DESCRIPTION)] = "fixture",
    search: Annotated[
        str,
        Query(
            max_length=100,
            description=(
                "Búsqueda local sin distinguir mayúsculas: ID, código, activo, nombre, empresa "
                "y proyecto del equipo; ID y proyecto de solicitudes. Conserva relaciones por "
                "maquinaria_id exacto. No busca fuera de las páginas leídas ni filtra estados."
            ),
            examples=["CF-03", "PROY-014"],
        ),
    ] = "",
) -> HubResponse:
    response.headers["Cache-Control"] = "no-store"
    return read_hub(
        request.app.state.settings,
        request.app.state.nexus,
        mode,
        search,
        engine=request.app.state.engine,
        startrack=request.app.state.startrack,
    )

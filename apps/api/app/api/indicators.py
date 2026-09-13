from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.api.documentation import MODE_DESCRIPTION
from app.models.hub import DataMode
from app.models.indicators import IndicatorsReport
from app.services.hub import read_hub
from app.services.indicators import compute_indicators

router = APIRouter(prefix="/api/v1", tags=["Indicadores"])


@router.get(
    "/indicators",
    summary=(
        "Indicadores calculables por fila: sin promedios; ausencia no es cero; fixture sin corte"
    ),
    description=(
        "Fichas y filas de los indicadores que hoy se pueden calcular con las lecturas existentes: "
        "tiempo de aprobación (approved_at − created_at), antigüedad de la solicitud abierta al "
        "corte, aprobadas con unidad sin tarea enviada, OCUPADA sin proyecto, asignación vencida, "
        "tarea completada sin recepción, falla activa registrada y antigüedad de la evidencia del "
        "registro. Usa la misma lectura acotada de Prisma que /hub (mismo mode y search) y una "
        "página del registro local de movimientos (hasta 500); no consulta Startrack ni escribe "
        "nada. Advertencia: los resultados son por fila, sin promedios, percentiles ni "
        "porcentajes; la ausencia de un dato no es cero y se publica como no evaluable con el "
        "campo que falta; fixture no tiene corte de observación (data_as_of=null) ni tareas "
        "enviadas, así que las antigüedades y las ausencias no son evaluables en ese modo. "
        "Cada ficha (sheet) declara pregunta, decisión, grano, población, numerador, "
        "denominador, exclusiones, desconocidos, fechas exactas, unidad, responsable y regla de "
        "estado. Los conteos describen las filas de esta lectura (scope), no la flota. Con live "
        "deshabilitado responde 200 con alcance vacío y notas que lo explican; no hay fallback."
    ),
)
def get_indicators(
    request: Request,
    response: Response,
    mode: Annotated[DataMode, Query(description=MODE_DESCRIPTION)] = "fixture",
    search: Annotated[
        str,
        Query(
            max_length=100,
            description=(
                "Misma búsqueda local que /hub: ID, código, activo, nombre, empresa y proyecto "
                "del equipo; ID y proyecto de solicitudes. Conserva relaciones por maquinaria_id "
                "exacto. No busca fuera de las páginas leídas ni filtra estados."
            ),
            examples=["CF-03", "PROY-014"],
        ),
    ] = "",
) -> IndicatorsReport:
    response.headers["Cache-Control"] = "no-store"
    settings = request.app.state.settings
    hub = read_hub(
        settings,
        request.app.state.nexus,
        mode,
        search,
        engine=request.app.state.engine,
        startrack=request.app.state.startrack,
    )
    workflow = request.app.state.workflow.read(mode, page_size=500)
    return compute_indicators(hub, workflow)

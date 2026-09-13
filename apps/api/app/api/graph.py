from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.api.documentation import MODE_DESCRIPTION
from app.models.graph import GraphProjection
from app.models.hub import DataMode
from app.services.graph import build_graph
from app.services.hub import read_hub

router = APIRouter(prefix="/api/v1", tags=["Grafo operativo"])


@router.get(
    "/graph",
    summary="Proyección tipada de máquinas, solicitudes, proyectos, movimientos y lugares",
    description=(
        "Grafo de solo lectura sobre la misma lectura acotada de Prisma que /hub (mismo mode y "
        "search) y una página del registro local de movimientos (hasta 500); no consulta "
        "Startrack ni escribe nada. Cada nodo y arista lleva su evidencia (EvidenceRef con la "
        "procedencia intacta) y el alcance de la relación: current solo cuando la solicitud y la "
        "unidad almacenadas coinciden con los registros vigentes, historical si el origen cambió, "
        "unverifiable si la contraparte no está en la lectura. Los conflictos (hechos "
        "incompatibles) se separan de las tensiones (hechos a revisar) y de los faltantes "
        "(gaps, siempre «no verificable»). Revisar coverage: complete es false en fixture y "
        "mientras Startrack no se consulte; los proyectos y las unidades fuera de la página son "
        "nodos referenced_only; las listas vacías describen esta lectura, no la ausencia de "
        "registros. La presencia (observed_at_place) es del vehículo rastreado del movimiento, "
        "que puede ser el transportador, nunca de la máquina, y no acredita recepción. No hay "
        "geometría, ETA, distancias ni cercanías. Las muestras fixture no contienen tareas, "
        "visitas ni recepciones. Las alertas se copian del hub sin reevaluarlas."
    ),
)
def get_graph(
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
) -> GraphProjection:
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
    return build_graph(hub, workflow)

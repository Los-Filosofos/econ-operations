from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from app.api.documentation import MODE_DESCRIPTION
from app.models.hub import DataMode
from app.services.hub import read_hub
from app.services.integration_trace import IntegrationTrace, build_trace

router = APIRouter(prefix="/api/v1", tags=["Integración"])


@router.get(
    "/integration/{request_id}",
    summary="Recorrido de una solicitud: qué entra, cómo se transforma y qué devuelve",
    description=(
        "Deriva el mismo trace que muestra la página /integracion, sin escrituras remotas. "
        "stages describe las cuatro etapas (Prisma entrega, ECON normaliza, Startrack recibe, "
        "Startrack devuelve); field_map compara campo a campo con el tratamiento aplicado "
        "(Conservado, Transformado, Manual (operador) o Sin equivalente) y timeline reúne los "
        "instantes registrados. Sin movimiento guardado no se inventa un mapeo: se devuelve la "
        "preparación con missing_fields y blocking_reasons, y payload queda en null. "
        "ECON no estima tiempos de ruta; las duraciones solo aparecen cuando ambos extremos "
        "están registrados. Un 200 puede describir una etapa vacía."
    ),
    responses={
        404: {
            "description": (
                "La solicitud no está en la lectura acotada de este origen. No prueba que no "
                "exista en Prisma: revisar el origen y la cobertura de la consulta."
            )
        }
    },
)
def get_integration_trace(
    request: Request,
    response: Response,
    request_id: Annotated[
        str,
        Path(
            min_length=1,
            max_length=200,
            description=(
                "ID de la solicitud en el modelo de lectura (nexus:request:…) o el ID original "
                "de Prisma. Los nombres no identifican una solicitud."
            ),
            examples=["nexus:request:46d2573e-08d3-4855-971d-2fbf9564e135"],
        ),
    ],
    mode: Annotated[DataMode, Query(description=MODE_DESCRIPTION)] = "fixture",
) -> IntegrationTrace:
    response.headers["Cache-Control"] = "no-store"
    hub = read_hub(
        request.app.state.settings,
        request.app.state.nexus,
        mode,
        "",
        engine=request.app.state.engine,
        startrack=request.app.state.startrack,
    )
    trace = build_trace(hub, request_id, request.app.state.workflow.read(mode))
    if trace is None:
        raise HTTPException(
            status_code=404,
            detail="La solicitud no está en la lectura acotada de este origen.",
        )
    return trace

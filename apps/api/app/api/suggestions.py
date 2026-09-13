from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from app.api.documentation import MODE_DESCRIPTION
from app.models.hub import DataMode
from app.models.suggestions import AssignmentSuggestion
from app.services.hub import read_hub
from app.services.suggestions import suggest_assignment

router = APIRouter(prefix="/api/v1", tags=["Sugerencias"])


@router.get(
    "/requests/{request_id}/suggestions",
    summary=(
        "Unidades candidatas para una solicitud pendiente, sin asignar ni consultar proveedores"
    ),
    description=(
        "Sugerencia de solo lectura sobre la misma lectura acotada de Prisma que /hub (sin filtro "
        "de búsqueda) y el registro local de movimientos. Cada candidata lleva su nivel "
        "(eligible, review_required o excluded), los motivos por regla, las dos cadenas de clase "
        "comparadas y lo que la lectura no cubre como «no verificable». No hay puntajes, "
        "distancias, ETA ni presencia GPS: el dispositivo puede ser del transportador y una "
        "geocerca no prueba ubicación. Recomendar no es asignar: la asignación se registra en "
        "Prisma. applicable=false describe una solicitud no pendiente o ya vinculada; un 200 con "
        "cero elegibles no afirma que no exista una unidad, porque la cobertura es parcial "
        "(scope)."
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
def get_assignment_suggestions(
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
            examples=["nexus:request:0cbbbd77-4593-4791-9be5-afd46b06c888"],
        ),
    ],
    mode: Annotated[DataMode, Query(description=MODE_DESCRIPTION)] = "fixture",
) -> AssignmentSuggestion:
    response.headers["Cache-Control"] = "no-store"
    hub = read_hub(
        request.app.state.settings,
        request.app.state.nexus,
        mode,
        "",
        engine=request.app.state.engine,
        startrack=request.app.state.startrack,
    )
    suggestion = suggest_assignment(
        hub, request_id, request.app.state.workflow.read(mode, page_size=500)
    )
    if suggestion is None:
        raise HTTPException(
            status_code=404,
            detail="La solicitud no está en la lectura acotada de este origen.",
        )
    return suggestion

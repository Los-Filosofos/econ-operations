from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.documentation import MODE_DESCRIPTION, PLAN_EXAMPLES, WORKFLOW_CONFLICT
from app.integrations.startrack import Identifier
from app.models.hub import DataMode
from app.models.operations import MovementRecord
from app.models.workflow import MappingCatalogs, WorkflowOverview
from app.services.transfers import TransferMapping

router = APIRouter(prefix="/api/v1/operations", tags=["Traslados"])


class PlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: DataMode = Field(description=MODE_DESCRIPTION)
    mapping: TransferMapping = Field(
        description=(
            "IDs originales, geocerca y usuarios explícitos. No usar los IDs normalizados "
            "nexus:request:… o nexus:equipment:… ni unir registros por nombre. "
            "scheduled_date y scheduled_time programan el traslado en America/El_Salvador; "
            "las fechas de uso de la solicitud no se convierten en fechas de entrega."
        )
    )
    tracked_vehicle_id: Identifier | None = Field(
        default=None,
        description=(
            "ID explícito del vehículo rastreado en Startrack. Puede ser el transportador; "
            "su presencia GPS no prueba ubicación propia de la maquinaria ni recepción."
        ),
    )


class SyncInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: DataMode = Field(description=MODE_DESCRIPTION)


class ReceiptInput(SyncInput):
    receiver: str = Field(
        min_length=1, max_length=255, description="Nombre declarado de quien recibe."
    )
    received_at: datetime = Field(
        description=(
            "Instante de recepción ISO 8601 con zona horaria explícita, por ejemplo "
            "2026-09-14T14:00:00-06:00. Sin zona, el servicio rechaza la operación con 409."
        )
    )
    reference: str = Field(
        min_length=1,
        max_length=255,
        description="Referencia de la constancia de recepción; no sube ni verifica un archivo.",
    )
    note: str | None = Field(default=None, max_length=2000, description="Nota de la declaración.")


MovementIdPath = Annotated[
    str,
    Path(description="UUID local devuelto en MovementRecord.id, no el ID de tarea de Startrack."),
]


@router.get(
    "",
    summary="Consultar planes e historial de movimientos",
    description=(
        "Lee el registro local del modo elegido, sin sincronizar proveedores. Devuelve hasta "
        "100 movimientos; complete indica si la consulta cubre todos los registros del filtro. "
        "available=false explica registro SQL inaccesible o live deshabilitado, también con 200. "
        "La ausencia de movimientos con cobertura incompleta no acredita ausencia de traslados. "
        "last_sync_at es el último corte guardado del modo, no una fecha de actualización de "
        "cada tarea. management_enabled y sending_enabled son capacidades de esta petición."
    ),
)
def list_operations(
    request: Request,
    mode: Annotated[DataMode, Query(description=MODE_DESCRIPTION)] = "fixture",
    request_source_id: Annotated[
        str | None,
        Query(
            max_length=255,
            description="ID original exacto de la solicitud Prisma; omitir para consultar el modo.",
            examples=["46d2573e-08d3-4855-971d-2fbf9564e135"],
        ),
    ] = None,
) -> WorkflowOverview:
    return request.app.state.workflow.read(mode, request_source_id)


@router.get(
    "/catalogs",
    summary="Consultar catálogos acotados de Startrack",
    description=(
        "Consulta geocercas, usuarios, vehículos y tipos de tarea del sandbox. Esta ruta siempre "
        "usa live: no declara parámetro mode; añadir mode=fixture no cambia el origen. "
        "No fabrica catálogos locales. Requiere lecturas live "
        "y credenciales de Startrack en el servidor. complete=false conserva el límite de "
        "cobertura; la ausencia de un ID en esta respuesta no demuestra que no exista."
    ),
    responses=WORKFLOW_CONFLICT,
)
def mapping_catalogs(request: Request) -> MappingCatalogs:
    return request.app.state.workflow.catalogs()


@router.post(
    "/plans",
    status_code=201,
    summary="Guardar un plan local de traslado",
    description=(
        "Guarda correspondencias, registros de origen y resultado de preparación. No crea "
        "tareas ni modifica Prisma. Requiere gestión local y esquema SQL migrado. Un 201 puede "
        "guardar state=blocked: revisar preparation.blocking_reasons y missing_fields. "
        "Repetir la misma referencia y contenido devuelve el mismo movimiento; reutilizarla "
        "con otra identidad produce conflicto. fixture permite ensayar el guardado, pero "
        "no encolar ni declarar recepción. En live consulta solicitud y maquinaria por ID."
    ),
    responses=WORKFLOW_CONFLICT,
)
def save_plan(
    request: Request, body: Annotated[PlanInput, Body(openapi_examples=PLAN_EXAMPLES)]
) -> MovementRecord:
    return request.app.state.workflow.save_plan(
        body.mode, body.mapping, tracked_vehicle_id=body.tracked_vehicle_id
    )


@router.post(
    "/{movement_id}/queue",
    summary="Validar y encolar un movimiento live",
    description=(
        "Opera únicamente sobre un plan live. Exige gestión local, lecturas y escrituras "
        "live habilitadas y credenciales de ambos proveedores. Relee aprobación/asignación, "
        "valida catálogos y busca tareas previas por referencia antes de encolar. No envía "
        "el POST remoto en esta petición: la sincronización o el worker procesa la cola. "
        "Una búsqueda incompleta o coincidencia existente impide encolar."
    ),
    responses=WORKFLOW_CONFLICT,
)
def queue_movement(request: Request, movement_id: MovementIdPath) -> MovementRecord:
    return request.app.state.workflow.queue(movement_id)


@router.post(
    "/sync",
    summary="Ejecutar un ciclo de sincronización",
    description=(
        "Requiere gestión local. fixture guarda un corte documental sin llamadas remotas. "
        "live consulta orígenes, revalida planes, puede encolar si AUTO_QUEUE_TRANSFERS está "
        "habilitado y enviar hasta 10 tareas por ciclo con las habilitaciones de escritura. "
        "Consulta seguimiento y concilia resultados inciertos sin repetir automáticamente "
        "el POST de creación. No es una consulta inocua en live. Un 200 puede contener "
        "advertencias parciales en message; revisar movimientos, estados y fechas."
    ),
    responses=WORKFLOW_CONFLICT,
)
def sync_operations(
    request: Request,
    body: Annotated[
        SyncInput,
        Body(
            openapi_examples={
                "local_sample": {
                    "summary": "Guardar un corte local de las muestras",
                    "value": {"mode": "fixture"},
                }
            }
        ),
    ],
) -> WorkflowOverview:
    return request.app.state.workflow.sync(body.mode)


@router.post(
    "/{movement_id}/receipt",
    summary="Registrar una declaración explícita de recepción",
    description=(
        "Requiere gestión local, mode=live y movimiento sent con job_id. No admite fixture. "
        "Conserva receptor, instante con zona y referencia de constancia como declaración "
        "manual; no verifica firma ni archivo. Una tarea completada o presencia en geocerca "
        "no la genera automáticamente. Repetir una declaración idéntica conserva la original; "
        "cambiar una recepción ya guardada produce 409. No modifica Prisma ni Startrack."
    ),
    responses=WORKFLOW_CONFLICT,
)
def receive_movement(
    request: Request,
    movement_id: MovementIdPath,
    body: Annotated[
        ReceiptInput,
        Body(
            openapi_examples={
                "format_only": {
                    "summary": "Formato didáctico; requiere un movimiento live ya enviado",
                    "description": "No ejecutar con una persona o constancia inventadas.",
                    "value": {
                        "mode": "live",
                        "receiver": "Receptor del ejemplo",
                        "received_at": "2026-09-14T14:00:00-06:00",
                        "reference": "demo-constancia-001",
                        "note": "Ejemplo de formato; no representa recepción observada.",
                    },
                }
            }
        ),
    ],
) -> MovementRecord:
    return request.app.state.workflow.record_receipt(movement_id, **body.model_dump())

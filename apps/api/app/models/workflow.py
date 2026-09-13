from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.operations import MovementRecord


class OperationsCoverage(BaseModel):
    total: int = 0
    displayed: int = 0
    page: int = 1
    page_size: int = 100
    total_pages: int = 1
    has_more: bool = False
    is_complete: bool = True
    note: str = ""


class WorkflowOverview(BaseModel):
    available: bool
    message: str
    complete: bool = Field(
        default=False,
        description=(
            "Indica si todos los movimientos locales del modo y filtro de solicitud caben "
            "en esta lectura acotada. No acredita cobertura de los proveedores."
        ),
    )
    management_enabled: bool = False
    sending_enabled: bool = False
    movements: list[MovementRecord] = Field(default_factory=list)
    last_sync_at: datetime | None = Field(
        default=None,
        description=(
            "Última lectura del origen guardada para el modo: fecha del último corte o de "
            "su confirmación posterior sin cambios (max(recorded_at, last_confirmed_at)). "
            "No es la fecha de actualización de cada tarea."
        ),
    )
    total: int = 0
    page: int = 1
    page_size: int = 100
    total_pages: int = 1
    coverage: OperationsCoverage | None = None


class MappingCatalogs(BaseModel):
    observed_at: datetime
    complete: bool = False
    message: str = "Catálogos acotados; vincula por ID y confirma el destino y responsable."
    pois: list[dict[str, Any]]
    users: list[dict[str, Any]]
    vehicles: list[dict[str, Any]]
    job_types: list[dict[str, Any]]

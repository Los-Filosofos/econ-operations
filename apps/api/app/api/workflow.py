from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.integrations.startrack import Identifier
from app.models.hub import DataMode
from app.models.operations import MovementRecord
from app.models.workflow import MappingCatalogs, WorkflowOverview
from app.services.transfers import TransferMapping

router = APIRouter(prefix="/api/v1/operations", tags=["Traslados"])


class PlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: DataMode
    mapping: TransferMapping
    tracked_vehicle_id: Identifier | None = None


class SyncInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: DataMode


class ReceiptInput(SyncInput):
    receiver: str = Field(min_length=1, max_length=255)
    received_at: datetime
    reference: str = Field(min_length=1, max_length=255)
    note: str | None = Field(default=None, max_length=2000)


@router.get("")
def list_operations(
    request: Request,
    mode: DataMode = "fixture",
    request_source_id: Annotated[str | None, Query(max_length=255)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 100,
) -> WorkflowOverview:
    return request.app.state.workflow.read(
        mode,
        request_source_id,
        page=page,
        page_size=page_size,
    )


@router.get("/catalogs")
def mapping_catalogs(request: Request) -> MappingCatalogs:
    return request.app.state.workflow.catalogs()


@router.post("/plans", status_code=201)
def save_plan(request: Request, body: PlanInput) -> MovementRecord:
    return request.app.state.workflow.save_plan(
        body.mode, body.mapping, tracked_vehicle_id=body.tracked_vehicle_id
    )


@router.post("/{movement_id}/queue")
def queue_movement(request: Request, movement_id: str) -> MovementRecord:
    return request.app.state.workflow.queue(movement_id)


@router.post("/sync")
def sync_operations(request: Request, body: SyncInput) -> WorkflowOverview:
    return request.app.state.workflow.sync(body.mode)


@router.post("/{movement_id}/receipt")
def receive_movement(request: Request, movement_id: str, body: ReceiptInput) -> MovementRecord:
    return request.app.state.workflow.record_receipt(movement_id, **body.model_dump())

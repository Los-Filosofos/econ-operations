"""Application workflow shared by Dash, HTTP and the explicitly enabled worker."""

from datetime import UTC, datetime, time, timedelta
from functools import wraps
from threading import Lock

from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.access import management_allowed, management_scope
from app.core.config import Settings
from app.integrations.fixtures import fixture_records
from app.integrations.nexus import NexusConnector, NexusReadError, NexusSnapshot
from app.integrations.startrack import (
    StartrackClient,
    StartrackJob,
    StartrackReadError,
    StartrackTaskDraft,
    StartrackWriteRejected,
    StartrackWriteUnknown,
)
from app.models.hub import DataMode, EquipmentRecord, Provenance, RequestRecord
from app.models.operations import MovementRecord
from app.models.workflow import MappingCatalogs, WorkflowOverview
from app.services.hub import BUSINESS_TIMEZONE, _map_live, read_hub
from app.services.ledger import LedgerError, OperationsLedger
from app.services.transfers import TransferMapping, prepare_transfer


class WorkflowError(Exception):
    """Public messages contain neither credentials nor provider/database payloads."""


def _boundary(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except (LedgerError, NexusReadError, StartrackReadError) as error:
            raise WorkflowError(str(error)) from None
        except ValidationError:
            raise WorkflowError("El registro de operación requiere revisar su formato.") from None
        except SQLAlchemyError:
            raise WorkflowError(
                "El registro de operaciones no está disponible. Revisa la conexión y la migración."
            ) from None

    return wrapped


def _instant(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


class WorkflowService:
    def __init__(
        self, settings: Settings, engine: Engine, nexus: NexusConnector, startrack: StartrackClient
    ):
        self.settings = settings
        self.nexus = nexus
        self.startrack = startrack
        self.ledger = OperationsLedger(engine)
        self._sync_lock = Lock()

    def _mode(self, mode: str) -> None:
        if mode not in {"fixture", "live"}:
            raise WorkflowError("Origen de datos inválido.")
        if mode == "live" and not self.settings.allow_live_reads:
            raise WorkflowError("Las lecturas en vivo están deshabilitadas en este servidor.")

    def _manage(self, mode: str) -> None:
        self._mode(mode)
        if not self.settings.allow_local_management or not management_allowed():
            raise WorkflowError("La gestión está habilitada únicamente desde el servidor local.")

    def _send_enabled(self) -> bool:
        return bool(
            self.settings.allow_live_reads
            and self.settings.allow_live_writes
            and self.nexus.configured
            and self.startrack.configured
            and self.startrack.config.enabled
            and self.startrack.config.allow_writes
        )

    def _send_gate(self) -> None:
        self._manage("live")
        if not self._send_enabled():
            raise WorkflowError(
                "El envío requiere habilitación y credenciales de ambos proveedores."
            )

    def read(self, mode: DataMode, request_source_id: str | None = None) -> WorkflowOverview:
        try:
            self._mode(mode)
            movements = self.ledger.list(mode, request_source_id=request_source_id)
            snapshot = self.ledger.last_snapshot(mode)
        except WorkflowError as error:
            return WorkflowOverview(available=False, message=str(error))
        except SQLAlchemyError:
            return WorkflowOverview(
                available=False,
                message=(
                    "Registro no disponible: revisa la conexión y aplica la migración del servidor."
                ),
            )
        enabled = self.settings.allow_local_management and management_allowed()
        return WorkflowOverview(
            available=True,
            message=(
                "Planes locales sobre las muestras proporcionadas. No se envían a Startrack."
                if mode == "fixture"
                else "Movimientos del sandbox: tarea, presencia GPS y recepción separadas."
            ),
            management_enabled=enabled,
            sending_enabled=enabled and mode == "live" and self._send_enabled(),
            movements=movements,
            last_sync_at=snapshot.recorded_at if snapshot else None,
        )

    def _source_records(
        self, mode: DataMode, request_source_id: str
    ) -> tuple[RequestRecord, EquipmentRecord | None]:
        self._mode(mode)
        if mode == "fixture":
            equipment, requests = fixture_records()
        else:
            request = self.nexus.get_request(request_source_id)
            machine = (
                self.nexus.get_equipment(request.maquinaria_id) if request.maquinaria_id else None
            )
            equipment, requests = _map_live(
                NexusSnapshot(
                    equipment=[machine] if machine else [],
                    requests=[request],
                    equipment_total=1 if machine else 0,
                    requests_total=1,
                    complete=False,
                ),
                datetime.now(UTC),
            )
        request = next(
            (item for item in requests if item.provenance.source_id == request_source_id), None
        )
        if request is None:
            raise WorkflowError("La solicitud no se encontró en el origen seleccionado.")
        return request, next((item for item in equipment if item.id == request.machinery_id), None)

    @_boundary
    def save_plan(
        self, mode: DataMode, mapping: TransferMapping, tracked_vehicle_id: str | None = None
    ) -> MovementRecord:
        self._manage(mode)
        request, equipment = self._source_records(mode, mapping.request_source_id)
        return self.ledger.create(
            mode, request, equipment, mapping, tracked_vehicle_id=tracked_vehicle_id
        )

    @_boundary
    def catalogs(self) -> MappingCatalogs:
        self._mode("live")
        return MappingCatalogs(
            observed_at=datetime.now(UTC),
            pois=[item.model_dump() for item in self.startrack.list_pois().items],
            users=[item.model_dump() for item in self.startrack.list_users().items],
            vehicles=[item.model_dump() for item in self.startrack.list_vehicles().items],
            job_types=[item.model_dump() for item in self.startrack.list_job_types().items],
        )

    def _validate_catalogs(self, movement: MovementRecord) -> None:
        mapping = TransferMapping.model_validate(movement.mapping)
        if mapping.poi_id not in {item.id for item in self.startrack.list_pois().items}:
            raise WorkflowError("Destino sin validar en el catálogo acotado de geocercas.")
        users = {item.id for item in self.startrack.list_users().items}
        if not set(mapping.assigned_user_ids).issubset(users):
            raise WorkflowError("Hay usuarios sin validar en el catálogo de Startrack.")
        if mapping.job_type_id:
            job_types = {
                item.id
                for item in self.startrack.list_job_types().items
                if item.deactivated in {None, False, "0", "false"}
            }
            if mapping.job_type_id not in job_types:
                raise WorkflowError("Tipo de tarea sin validar o desactivado en Startrack.")
        if movement.tracked_vehicle_id:
            vehicles = {
                item.id
                for item in self.startrack.list_vehicles().items
                if item.deactivated in {None, "0", "false"}
            }
            if movement.tracked_vehicle_id not in vehicles:
                raise WorkflowError("Vehículo GPS sin validar en el catálogo acotado.")

    def _fresh_plan(self, movement: MovementRecord):
        request, equipment = self._source_records("live", movement.request_source_id)
        mapping = TransferMapping.model_validate(movement.mapping)
        preparation = prepare_transfer(request, equipment, mapping)
        if movement.state in {"draft", "blocked"}:
            movement = self.ledger.revalidate(movement.id, "live", request, equipment, preparation)
        if preparation.draft is None:
            raise WorkflowError("La aprobación o asignación actual requiere revisión en Prisma.")
        if preparation.draft.payload() != movement.payload:
            raise WorkflowError("La solicitud cambió desde la preparación; revisa el movimiento.")
        return preparation.draft

    @_boundary
    def queue(self, movement_id: str) -> MovementRecord:
        self._send_gate()
        movement = self.ledger.get(movement_id, "live")
        self._fresh_plan(movement)
        self._validate_catalogs(movement)
        existing = self.startrack.find_jobs_by_remote_id(movement.movement_reference)
        if existing.items:
            raise WorkflowError("Ya existen tareas con esa referencia. Revisa la correspondencia.")
        if not existing.exhausted:
            raise WorkflowError(
                "La búsqueda de tareas previas quedó incompleta; revisa la referencia."
            )
        return self.ledger.queue(movement_id, "live")

    @_boundary
    def record_receipt(
        self,
        movement_id: str,
        mode: DataMode,
        receiver: str,
        received_at: datetime,
        reference: str,
        note: str | None = None,
    ) -> MovementRecord:
        self._manage(mode)
        return self.ledger.record_receipt(
            movement_id,
            mode,
            receiver=receiver,
            received_at=received_at,
            reference=reference,
            note=note,
        )

    @staticmethod
    def _matches_job(movement: MovementRecord, job: StartrackJob) -> bool:
        draft = StartrackTaskDraft.model_validate(movement.payload)
        return bool(
            job.remote_id == draft.remote_id
            and job.poi_id == draft.poi_id
            and job.objective == draft.objective
            and job.start_date == draft.start_date.isoformat()
            and set(job.assigned_user_ids or []) == set(draft.assigned_user_ids)
            and (draft.job_type_id is None or job.job_type_id == draft.job_type_id)
            and (draft.start_time is None or job.start_time == draft.start_time)
            and (draft.description is None or job.description == draft.description)
            and (draft.form_ids is None or set(job.form_ids or []) == set(draft.form_ids))
            and (
                draft.required_form_ids is None
                or set(job.required_form_ids or []) == set(draft.required_form_ids)
            )
        )

    @staticmethod
    def _acknowledges_draft(draft: StartrackTaskDraft, job: StartrackJob) -> bool:
        """Missing optional echoes are allowed; supplied contradictions remain uncertain."""
        expected = draft.payload()
        actual = job.model_dump(exclude_none=True)
        for field in (
            "objective",
            "start_date",
            "start_time",
            "description",
            "remote_id",
            "poi_id",
            "job_type_id",
            "assigned_user_ids",
            "form_ids",
            "required_form_ids",
        ):
            if field not in expected or field not in actual:
                continue
            if isinstance(expected[field], list):
                if set(expected[field]) != set(actual[field]):
                    return False
            elif expected[field] != actual[field]:
                return False
        return True

    def _dispatch(self, movement: MovementRecord) -> None:
        # The durable claim is already committed. Any unexpected crash is reconciled
        # as unknown, never automatically converted into another create attempt.
        try:
            self._send_gate()
            draft = self._fresh_plan(movement)
            self._validate_catalogs(movement)
            existing = self.startrack.find_jobs_by_remote_id(movement.movement_reference)
            if existing.items or not existing.exhausted:
                self.ledger.finish_unknown(movement.id, "mapping_conflict")
                return
        except (WorkflowError, NexusReadError, StartrackReadError, LedgerError, ValidationError):
            self.ledger.finish_failed(movement.id, "dispatch_blocked")
            return
        try:
            job = self.startrack.create_job(draft)
        except StartrackWriteRejected:
            self.ledger.finish_failed(movement.id, "provider_rejected")
        except StartrackWriteUnknown:
            self.ledger.finish_unknown(movement.id, "ambiguous_response")
        else:
            # The SDK validates the creation envelope, source ID and remote_id
            # when supplied. Optional fields may be omitted in that response.
            # Full correlation is needed for unknown outcomes, not an acknowledged POST.
            if not self._acknowledges_draft(draft, job):
                self.ledger.finish_unknown(movement.id, "invalid_response")
                return
            self.ledger.finish_sent(movement.id, job.id, status=job.status)

    def _observe(self, movement: MovementRecord, statuses: dict[str, str | None]) -> None:
        if movement.state == "unknown":
            result = self.startrack.find_jobs_by_remote_id(movement.movement_reference)
            # A truncated result cannot establish a unique correlation.
            if (
                not result.exhausted
                or len(result.items) != 1
                or not self._matches_job(movement, result.items[0])
            ):
                return
            job = result.items[0]
            movement = self.ledger.finish_sent(movement.id, job.id, status=job.status)
        elif movement.state == "sent" and movement.job_id:
            job = self.startrack.get_job(movement.job_id)
            if job is None:
                raise WorkflowError("La tarea vinculada no apareció en la lectura acotada.")
        else:
            return
        now = datetime.now(UTC)
        provenance = Provenance(
            source="startrack",
            source_id=job.id,
            environment="sandbox",
            observed_at=now,
            is_synthetic=True,
        )
        self.ledger.record_observation(
            movement.id,
            "live",
            kind="task_state",
            source_id=job.id,
            event_time=_instant(job.last_status_change_date or job.closed_date or job.changed_date),
            observed_at=now,
            data={
                "job_id": job.id,
                "status": job.status,
                "workflow_role": statuses.get(job.status),
                "poi_id": job.poi_id,
                "remote_id": job.remote_id,
                "objective": job.objective,
                "start_date": job.start_date,
                "changed_date": job.changed_date,
                "closed_date": job.closed_date,
                "last_status_change_date": job.last_status_change_date,
            },
            provenance=provenance,
        )
        if not movement.tracked_vehicle_id:
            return
        mapping = TransferMapping.model_validate(movement.mapping)
        if job.poi_id != mapping.poi_id:
            raise WorkflowError(
                "El destino actual de la tarea requiere revisar la correspondencia."
            )
        today = datetime.now(BUSINESS_TIMEZONE).date()
        if mapping.scheduled_date > today:
            return
        # Reporting is explicitly bounded; old movements retain visible gaps.
        start = max(mapping.scheduled_date, today - timedelta(days=6))
        visits = self.startrack.list_visits(
            start_date=start,
            end_date=today,
            poi_ids=(mapping.poi_id,),
            vehicle_ids=(movement.tracked_vehicle_id,),
        )
        planned = datetime.combine(
            mapping.scheduled_date,
            time.fromisoformat(mapping.scheduled_time or "00:00:00"),
            BUSINESS_TIMEZONE,
        )
        for visit in visits.items:
            event_time = _instant(visit.start_date)
            # Unzoned provider values are kept by its adapter, but cannot prove
            # temporal correspondence here. Neither presence nor task closure is receipt.
            if (
                visit.poi_id != mapping.poi_id
                or visit.vehicle_id != movement.tracked_vehicle_id
                or event_time is None
                or event_time < planned
                or event_time > visits.observed_at
            ):
                continue
            self.ledger.record_observation(
                movement.id,
                "live",
                kind="arrival",
                source_id=visit.id,
                event_time=event_time,
                observed_at=visits.observed_at,
                data={
                    "visit_id": visit.id,
                    "poi_id": visit.poi_id,
                    "tracked_asset_id": visit.vehicle_id,
                    "event_time_raw": visit.start_date,
                    "label": "Presencia del vehículo GPS en destino; no acredita recepción.",
                },
                provenance=provenance.model_copy(
                    update={"source_id": visit.id, "observed_at": visits.observed_at}
                ),
            )

    @_boundary
    def sync(self, mode: DataMode) -> WorkflowOverview:
        self._manage(mode)
        if not self._sync_lock.acquire(blocking=False):
            raise WorkflowError("Ya hay una sincronización en curso en este proceso.")
        try:
            hub = read_hub(self.settings, self.nexus, mode)
            self.ledger.record_snapshot(hub)
            messages = []
            if mode == "live":
                if not any(
                    s.id == "nexus" and s.status in {"connected", "partial"} for s in hub.sources
                ):
                    messages.append("Prisma no respondió; consulta el estado de fuentes.")
                self.ledger.recover_stale_sending(datetime.now(UTC) - timedelta(minutes=10))
                # Refresh every saved plan against detail endpoints, so approval
                # and assignment changes are detected even outside the list page.
                for movement in self.ledger.list("live"):
                    if movement.state in {"draft", "blocked"}:
                        try:
                            self._fresh_plan(movement)
                            if self.settings.auto_queue_transfers and self._send_enabled():
                                self.queue(movement.id)
                        except (WorkflowError, NexusReadError, StartrackReadError, LedgerError):
                            messages.append(
                                "Hay planes que requieren revisar origen o correspondencias."
                            )
                if self._send_enabled():
                    for _ in range(10):
                        movement = self.ledger.claim()
                        if movement is None:
                            break
                        self._dispatch(movement)
                if self.startrack.configured:
                    try:
                        statuses = {
                            item.id: item.workflow_role
                            for item in self.startrack.list_job_statuses().items
                        }
                        for movement in self.ledger.list("live"):
                            try:
                                self._observe(movement, statuses)
                            except (WorkflowError, StartrackReadError, LedgerError):
                                messages.append(
                                    "Seguimiento parcial: hay evidencia pendiente de consultar."
                                )
                    except StartrackReadError:
                        messages.append("Startrack no respondió; el registro previo se conserva.")
                else:
                    messages.append("Faltan credenciales de Startrack; no se consultó seguimiento.")
            result = self.read(mode)
            if messages:
                result.message = " ".join(dict.fromkeys(messages))
            return result
        finally:
            self._sync_lock.release()

    def run_cycle(self, mode: DataMode = "live") -> WorkflowOverview:
        """CLI-only entry point; settings still gate all reads and remote writes."""
        with management_scope(self.settings.allow_local_management):
            return self.sync(mode)

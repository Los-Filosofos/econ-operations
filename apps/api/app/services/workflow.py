"""Application workflow shared by Dash, HTTP and the explicitly enabled worker.

Every transition carries the actor that caused it: the session user (HTTP or Dash),
the loopback developer without a login (`local_dev`) or the CLI worker (`cli_worker`).
No user is ever invented; when nothing is known the actor is None.
"""

from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from functools import wraps
from threading import Lock

from dash.exceptions import AppNotFoundError
from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.access import management_allowed, management_scope
from app.core.auth import Permission, actor_from_user, can, session_user
from app.core.config import Settings
from app.core.database import cycle_lock
from app.integrations.fixtures import fixture_records
from app.integrations.nexus import NexusConnector, NexusReadError
from app.integrations.startrack import (
    StartrackClient,
    StartrackJob,
    StartrackReadError,
    StartrackTaskDraft,
    StartrackWriteRejected,
    StartrackWriteUnknown,
)
from app.models.hub import DataMode, EquipmentRecord, Provenance, RequestRecord
from app.models.operations import Actor, MovementRecord
from app.models.workflow import MappingCatalogs, OperationsCoverage, WorkflowOverview
from app.services.hub import BUSINESS_TIMEZONE, map_live, read_hub
from app.services.ledger import (
    SAFE_REASON_CODES,
    LedgerError,
    MovementConflict,
    OperationsLedger,
    effective_event_sort_key,
    last_read_at,
)
from app.services.transfers import TransferMapping, prepare_transfer

ACTIVE = {None, False, "0", "false"}
DENIED = "La gestión requiere una sesión con permiso para esta operación."
OBSERVED_JOB_FIELDS = {
    "status",
    "poi_id",
    "remote_id",
    "objective",
    "start_date",
    "creation_date",
    "changed_date",
    "closed_date",
    "last_status_change_date",
    "start_time",
    "duration",
    "poi_name",
    "completed_lat",
    "completed_lon",
}
# Provider workflow roles that end a task: '1' completed, '2' cancelled. Reaching one of
# them closes the movement's window for GPS attribution; it never proves receipt.
CLOSING_ROLES = frozenset({"1", "2"})
# A POST answered with a job already linked to another movement is closed as failed with
# this code and is never repeated. `job_conflict` is used as soon as the ledger admits it.
JOB_CONFLICT_REASON = "job_conflict" if "job_conflict" in SAFE_REASON_CODES else "mapping_conflict"
ARRIVAL_LABELS = {
    None: "Presencia del vehículo GPS en destino; no acredita recepción.",
    "machine_device": "Presencia del vehículo GPS en destino; no acredita recepción.",
    "transporter": (
        "Presencia del vehículo del transportador en destino; no acredita recepción "
        "ni ubicación de la máquina."
    ),
}
CLI_WORKER = Actor(kind="cli_worker")


class WorkflowError(Exception):
    """Public messages contain neither credentials nor provider/database payloads."""


class SyncInProgress(WorkflowError):
    """Another cycle owns this process's lock or the cross-process advisory lock."""


PROVIDER_ERRORS = (WorkflowError, NexusReadError, StartrackReadError, LedgerError)


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
    """Only zoned provider timestamps become instants; unzoned values stay unknown."""
    try:
        parsed = datetime.fromisoformat(value) if value else None
    except ValueError:
        return None
    return parsed if parsed and parsed.tzinfo else None


def _corresponds(draft: StartrackTaskDraft, job: StartrackJob, *, strict: bool) -> bool:
    """Compare documented draft fields with a provider job; lists compare as sets.

    strict requires every draft field to be echoed (unknown-outcome reconciliation);
    otherwise omitted optional echoes are tolerated but contradictions are not.
    """
    actual = job.model_dump(exclude_none=True)
    for field, expected in draft.payload().items():
        if field == "notify_contact":
            continue
        if field not in actual:
            if strict:
                return False
            continue
        if isinstance(expected, list):
            if set(expected) != set(actual[field]):
                return False
        elif expected != actual[field]:
            return False
    return True


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

    def _manage(
        self, mode: str, permission: Permission = Permission.manage_transfers
    ) -> Actor | None:
        """Check the acting user's role and return who acts when the caller passed nobody.

        Request authority comes from main.py (role or local dev mode); Dash callbacks share
        one management scope, so the acting user's role is checked per action here. The
        session user becomes a `session` actor; a Dash request without a login is only
        possible in development (`local_dev`); without a Dash application (CLI worker,
        isolated tests) nothing is known and None is returned. No user is ever invented.
        """
        self._mode(mode)
        if not management_allowed():
            raise WorkflowError(DENIED)
        try:
            user = session_user()
        except AppNotFoundError:  # CLI worker or isolated tests: no Dash application
            return None
        if user is None:
            if self.settings.auth_required:
                return None
            return actor_from_user(None, kind="local_dev")
        if not can(user.role, permission):
            raise WorkflowError(DENIED)
        return actor_from_user(user, kind="session")

    @staticmethod
    def _actor(explicit: Actor | None, fallback: Actor | None) -> Actor | None:
        """The caller's actor wins; the gate has already run in every case."""
        return explicit if explicit is not None else fallback

    def _send_enabled(self) -> bool:
        return bool(
            self.settings.allow_live_reads
            and self.settings.allow_live_writes
            and self.nexus.configured
            and self.startrack.configured
            and self.startrack.config.enabled
            and self.startrack.config.allow_writes
        )

    def _send_gate(self) -> Actor | None:
        actor = self._manage("live")
        if not self._send_enabled():
            raise WorkflowError(
                "El envío requiere habilitación y credenciales de ambos proveedores."
            )
        return actor

    def read(
        self,
        mode: DataMode,
        request_source_id: str | None = None,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> WorkflowOverview:
        page, page_size = max(1, page), max(1, min(page_size, 500))
        try:
            self._mode(mode)
            movements, total = self.ledger.list_page(
                mode,
                request_source_id=request_source_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
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
        enabled = management_allowed()
        total_pages = max(1, -(-total // page_size))
        complete = total == len(movements) and page == 1
        coverage = OperationsCoverage(
            total=total,
            displayed=len(movements),
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_more=page < total_pages,
            is_complete=complete,
            note=(
                f"Población completa: {total} movimientos registrados."
                if complete
                else f"Mostrando {len(movements)} de {total} movimientos registrados "
                f"(página {page} de {total_pages})."
            ),
        )
        if not complete:
            message = (
                f"Registro parcial: {coverage.note} Puede existir evidencia fuera de esta ventana."
            )
        elif mode == "fixture":
            message = "Planes locales sobre las muestras proporcionadas. No se envían a Startrack."
        else:
            message = "Movimientos del sandbox: tarea, presencia GPS y recepción separadas."
        return WorkflowOverview(
            available=True,
            complete=complete,
            message=message,
            management_enabled=enabled,
            sending_enabled=enabled and mode == "live" and self._send_enabled(),
            movements=movements,
            # Latest read of the source: the cut's record time or its later unchanged
            # confirmation (ADR 0006); an unchanged re-read inserts no cut.
            last_sync_at=last_read_at(snapshot) if snapshot else None,
            coverage=coverage,
            **coverage.model_dump(include={"total", "page", "page_size", "total_pages"}),
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
            equipment, requests = map_live(
                [machine] if machine else [], [request], datetime.now(UTC)
            )
        request = next((r for r in requests if r.provenance.source_id == request_source_id), None)
        if request is None:
            raise WorkflowError("La solicitud no se encontró en el origen seleccionado.")
        return request, next((e for e in equipment if e.id == request.machinery_id), None)

    @_boundary
    def save_plan(
        self,
        mode: DataMode,
        mapping: TransferMapping,
        tracked_vehicle_id: str | None = None,
        *,
        tracked_vehicle_kind: str | None = None,
        actor: Actor | None = None,
    ) -> MovementRecord:
        """Persist a plan. `tracked_vehicle_kind` is declared by the operator, never verified:
        the Startrack vehicle catalog has no type, so whether the device belongs to the
        machine or to its transporter is a statement that travels with the evidence."""
        actor = self._actor(actor, self._manage(mode))
        request, equipment = self._source_records(mode, mapping.request_source_id)
        return self.ledger.create(
            mode,
            request,
            equipment,
            mapping,
            tracked_vehicle_id=tracked_vehicle_id,
            tracked_vehicle_kind=tracked_vehicle_kind,
            actor=actor,
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
        if not set(mapping.assigned_user_ids) <= {i.id for i in self.startrack.list_users().items}:
            raise WorkflowError("Hay usuarios sin validar en el catálogo de Startrack.")
        if mapping.job_type_id and mapping.job_type_id not in {
            item.id for item in self.startrack.list_job_types().items if item.deactivated in ACTIVE
        }:
            raise WorkflowError("Tipo de tarea sin validar o desactivado en Startrack.")
        if movement.tracked_vehicle_id and movement.tracked_vehicle_id not in {
            item.id for item in self.startrack.list_vehicles().items if item.deactivated in ACTIVE
        }:
            raise WorkflowError("Vehículo GPS sin validar en el catálogo acotado.")

    def _fresh_plan(
        self, movement: MovementRecord, actor: Actor | None = None
    ) -> StartrackTaskDraft:
        request, equipment = self._source_records("live", movement.request_source_id)
        preparation = prepare_transfer(
            request, equipment, TransferMapping.model_validate(movement.mapping)
        )
        if movement.state in {"draft", "blocked"}:
            movement = self.ledger.revalidate(movement.id, "live", request, equipment, actor=actor)
        if preparation.draft is None:
            raise WorkflowError("La aprobación o asignación actual requiere revisión en Prisma.")
        if preparation.draft.payload() != movement.payload:
            raise WorkflowError("La solicitud cambió desde la preparación; revisa el movimiento.")
        return preparation.draft

    def _previous_jobs(self, movement: MovementRecord) -> None:
        existing = self.startrack.find_jobs_by_remote_id(movement.movement_reference)
        if existing.items:
            raise WorkflowError("Ya existen tareas con esa referencia. Revisa la correspondencia.")
        if not existing.exhausted:
            raise WorkflowError(
                "La búsqueda de tareas previas quedó incompleta; revisa la referencia."
            )

    @_boundary
    def queue(self, movement_id: str, *, actor: Actor | None = None) -> MovementRecord:
        actor = self._actor(actor, self._send_gate())
        movement = self.ledger.get(movement_id, "live")
        self._fresh_plan(movement, actor)
        self._validate_catalogs(movement)
        self._previous_jobs(movement)
        return self.ledger.queue(movement_id, "live", actor=actor)

    @_boundary
    def record_receipt(
        self,
        movement_id: str,
        mode: DataMode,
        *,
        receiver: str,
        received_at: datetime,
        reference: str,
        note: str | None = None,
        actor: Actor | None = None,
    ) -> MovementRecord:
        """`receiver` is the declared name; the session that declares it is kept apart."""
        actor = self._actor(actor, self._manage(mode, Permission.declare_reception))
        return self.ledger.record_receipt(
            movement_id,
            mode,
            receiver=receiver,
            received_at=received_at,
            reference=reference,
            note=note,
            declared_by=actor,
        )

    @_boundary
    def resolve(
        self, movement_id: str, *, reason_code: str, actor: Actor | None = None
    ) -> MovementRecord:
        """Operator exit from `unknown` to `failed` after checking the provider by hand.

        Local state only: nothing is sent to Startrack and the creation POST is never
        repeated. The `resolved` event records the actor and the permitted reason code.
        """
        actor = self._actor(actor, self._manage("live"))
        return self.ledger.resolve_unknown(
            movement_id, "live", reason_code=reason_code, actor=actor
        )

    def _dispatch(self, movement: MovementRecord, actor: Actor | None = None) -> None:
        # The durable claim is already committed. Any unexpected crash is reconciled
        # as unknown, never automatically converted into another create attempt.
        try:
            self._send_gate()
            draft = self._fresh_plan(movement, actor)
            self._validate_catalogs(movement)
            try:
                self._previous_jobs(movement)
            except WorkflowError:
                self.ledger.finish_unknown(movement.id, "mapping_conflict", actor=actor)
                return
        except (*PROVIDER_ERRORS, ValidationError):
            self.ledger.finish_failed(movement.id, "dispatch_blocked", actor=actor)
            return
        try:
            job = self.startrack.create_job(draft)
        except StartrackWriteRejected:
            self.ledger.finish_failed(movement.id, "provider_rejected", actor=actor)
        except StartrackWriteUnknown:
            self.ledger.finish_unknown(movement.id, "ambiguous_response", actor=actor)
        else:
            # The SDK validates the creation envelope, source ID and remote_id when
            # supplied; optional echoes may be omitted in an acknowledged POST.
            if not _corresponds(draft, job, strict=False):
                self.ledger.finish_unknown(movement.id, "invalid_response", actor=actor)
                return
            try:
                self.ledger.finish_sent(movement.id, job.id, status=job.status, actor=actor)
            except MovementConflict:
                # The answered job already belongs to another movement: this row cannot
                # own it, so it is closed without ever repeating the POST and the cycle
                # goes on with the next claim.
                self.ledger.finish_failed(movement.id, JOB_CONFLICT_REASON, actor=actor)

    @staticmethod
    def _closure(movement: MovementRecord) -> datetime | None:
        """Instant the linked task ended, from the latest task_state by the event policy.

        Only the most recent task state counts: a task that was reopened after being
        completed or cancelled has no closure, so the movement's window is open again.
        A closing state without a dated fact yields None (reading time never stands in).
        """
        states = [event for event in movement.events if event.kind == "task_state"]
        if not states:
            return None
        latest = max(states, key=effective_event_sort_key)
        if latest.data.get("workflow_role") in CLOSING_ROLES:
            return latest.event_time
        return None

    def _observe(
        self, movement: MovementRecord, statuses: dict[str, str | None], actor: Actor | None = None
    ) -> int:
        """Record the task state and the GPS visits within the movement's window.

        Returns how many visits of the tracked vehicle at the destination were left out
        because they fall outside the window (scheduled instant → task closure or read
        time); the cycle message makes that count visible.
        """
        if movement.state == "unknown":
            result = self.startrack.find_jobs_by_remote_id(movement.movement_reference)
            # A truncated result cannot establish a unique correlation.
            if not result.exhausted or len(result.items) != 1:
                return 0
            job = result.items[0]
            if not _corresponds(
                StartrackTaskDraft.model_validate(movement.payload), job, strict=True
            ):
                return 0
            movement = self.ledger.finish_sent(movement.id, job.id, status=job.status, actor=actor)
        elif movement.state == "sent" and movement.job_id:
            job = self.startrack.get_job(movement.job_id)
            if job is None:
                raise WorkflowError("La tarea vinculada no apareció en la lectura acotada.")
        else:
            return 0
        now = datetime.now(UTC)
        provenance = Provenance(
            source="startrack",
            source_id=job.id,
            environment="sandbox",
            observed_at=now,
            is_synthetic=True,
        )
        movement = self.ledger.record_observation(
            movement.id,
            "live",
            kind="task_state",
            source_id=job.id,
            event_time=_instant(job.last_status_change_date or job.closed_date or job.changed_date),
            observed_at=now,
            data={
                "job_id": job.id,
                "workflow_role": statuses.get(job.status),
                **job.model_dump(include=OBSERVED_JOB_FIELDS),
            },
            provenance=provenance,
            actor=actor,
        )
        if not movement.tracked_vehicle_id:
            return 0
        mapping = TransferMapping.model_validate(movement.mapping)
        if job.poi_id != mapping.poi_id:
            raise WorkflowError(
                "El destino actual de la tarea requiere revisar la correspondencia."
            )
        today = datetime.now(BUSINESS_TIMEZONE).date()
        if mapping.scheduled_date > today:
            return 0
        # The window closes with the task as just recorded, never with a stale closure.
        closure = self._closure(movement)
        # Reporting is explicitly bounded; old movements retain visible gaps.
        visits = self.startrack.list_visits(
            start_date=max(mapping.scheduled_date, today - timedelta(days=6)),
            end_date=today,
            poi_ids=(mapping.poi_id,),
            vehicle_ids=(movement.tracked_vehicle_id,),
        )
        planned = datetime.combine(
            mapping.scheduled_date,
            time.fromisoformat(mapping.scheduled_time or "00:00:00"),
            BUSINESS_TIMEZONE,
        )
        upper = min(visits.observed_at, closure or visits.observed_at)
        skipped = 0
        for visit in visits.items:
            event_time = _instant(visit.start_date)
            # Unzoned provider values are kept by its adapter, but cannot prove
            # temporal correspondence here. Neither presence nor task closure is receipt.
            if (
                visit.poi_id != mapping.poi_id
                or visit.vehicle_id != movement.tracked_vehicle_id
                or event_time is None
            ):
                continue
            if not planned <= event_time <= upper:
                skipped += 1
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
                    "tracked_asset_kind": movement.tracked_vehicle_kind,
                    "event_time_raw": visit.start_date,
                    "end_date_raw": visit.end_date,
                    "label": ARRIVAL_LABELS[movement.tracked_vehicle_kind],
                },
                provenance=provenance.model_copy(
                    update={"source_id": visit.id, "observed_at": visits.observed_at}
                ),
                actor=actor,
            )
        return skipped

    def _review(
        self,
        states: tuple[str, ...],
        limit: int,
        action: Callable[[MovementRecord], object],
        warning: str,
        *,
        delay_seconds: int = 0,
    ) -> list[str]:
        """Bounded, fair review queue: older plans are not starved by newer movements.

        `delay_seconds` is persisted in next_review_at, so a reviewed movement waits that
        long before any process reviews it again: the queue is ordered by next_review_at,
        so the first movement that is not yet due ends the batch.
        """
        messages = []
        now = datetime.now(UTC)
        for movement in self.ledger.select_for_review("live", states, limit=limit):
            if movement.next_review_at is not None and movement.next_review_at > now:
                break
            try:
                action(movement)
            except PROVIDER_ERRORS:
                messages.append(warning)
            finally:
                self.ledger.advance_review(movement.id, "live", delay_seconds=delay_seconds)
        return messages

    def _revalidate(self, movement: MovementRecord, actor: Actor | None = None) -> None:
        self._fresh_plan(movement, actor)
        if self.settings.auto_queue_transfers and self._send_enabled():
            self.queue(movement.id, actor=actor)

    def _cycle(self, mode: DataMode, actor: Actor | None) -> WorkflowOverview:
        """One bounded cycle; every ledger transition carries the same actor."""
        hub = read_hub(self.settings, self.nexus, mode)
        self.ledger.record_snapshot(hub)
        messages = []
        if mode == "live":
            if not any(
                s.id == "nexus" and s.status in {"connected", "partial"} for s in hub.sources
            ):
                messages.append("Prisma no respondió; consulta el estado de fuentes.")
            self.ledger.recover_stale_sending(
                datetime.now(UTC) - timedelta(minutes=10), actor=actor
            )
            messages += self._review(
                ("draft", "blocked"),
                self.settings.workflow_revalidation_batch_size,
                lambda movement: self._revalidate(movement, actor),
                "Hay planes que requieren revisar origen o correspondencias.",
                delay_seconds=self.settings.workflow_review_delay_seconds,
            )
            if self._send_enabled():
                for _ in range(10):
                    movement = self.ledger.claim(actor=actor)
                    if movement is None:
                        break
                    self._dispatch(movement, actor)
            if not self.startrack.configured:
                messages.append("Faltan credenciales de Startrack; no se consultó seguimiento.")
            else:
                try:
                    statuses = {
                        item.id: item.workflow_role
                        for item in self.startrack.list_job_statuses().items
                    }
                    outside_window: list[int] = []
                    messages += self._review(
                        ("sent", "unknown"),
                        self.settings.workflow_observation_batch_size,
                        lambda movement: outside_window.append(
                            self._observe(movement, statuses, actor)
                        ),
                        "Seguimiento parcial: hay evidencia pendiente de consultar.",
                    )
                    if sum(outside_window):
                        messages.append(
                            f"Visitas GPS fuera de la vigencia de su movimiento: "
                            f"{sum(outside_window)} no atribuidas."
                        )
                except StartrackReadError:
                    messages.append("Startrack no respondió; el registro previo se conserva.")
        result = self.read(mode)
        if messages:
            result.message = " ".join(dict.fromkeys(messages))
        return result

    @_boundary
    def sync(self, mode: DataMode, actor: Actor | None = None) -> WorkflowOverview:
        """Run one cycle under two locks: per process (threads) and per database (processes).

        The advisory lock in `cycle_lock` is defense in depth: the runbook already asks for
        a single worker per IP because provider report limits are shared, and Dash/HTTP
        callers may still trigger a cycle while the worker runs. It is released even when
        the cycle fails; a second process reports the cycle in progress without waiting.
        """
        actor = self._actor(actor, self._manage(mode))
        if not self._sync_lock.acquire(blocking=False):
            raise SyncInProgress("Ya hay una sincronización en curso en este proceso.")
        try:
            with cycle_lock(self.ledger.engine, f"econ:sync:{mode}") as owned:
                if not owned:
                    raise SyncInProgress("Ya hay una sincronización en curso en otro proceso.")
                return self._cycle(mode, actor)
        finally:
            self._sync_lock.release()

    def run_cycle(self, mode: DataMode = "live") -> WorkflowOverview:
        """CLI-only entry point; settings still gate all reads and remote writes.

        The worker acts as `cli_worker`: an actor without user, email or role.
        """
        with management_scope(True):
            return self.sync(mode, actor=CLI_WORKER)

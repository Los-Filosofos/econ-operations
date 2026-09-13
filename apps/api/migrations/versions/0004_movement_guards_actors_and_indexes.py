"""Movement guards in SQL, event actors, append-only events and index cleanup.

Revision ID: 0004_guards
Revises: 0003_users

Additive only. Columns are nullable, new indexes guard invariants that so far lived in
Python, and the append-only trigger exists on PostgreSQL only. No row is deleted, merged
or reassigned here: an existing violation makes the migration fail with IntegrityError
while creating the unique index, and an operator reconciles it by hand.

Stop the worker (and any `sync`) before migrating: the in-flight guard rejects a second
queued/sending/unknown movement per machine from the moment the index exists.

Pre-check queries to run before `alembic upgrade head` (both must return no rows)::

    -- a job_id linked to more than one movement per mode and environment
    SELECT mode, environment, job_id, count(*)
      FROM operation_movements
     WHERE job_id IS NOT NULL
     GROUP BY mode, environment, job_id
    HAVING count(*) > 1;

    -- more than one movement in flight for the same machine
    SELECT mode, environment, machinery_source_id, count(*)
      FROM operation_movements
     WHERE state IN ('queued', 'sending', 'unknown')
     GROUP BY mode, environment, machinery_source_id
    HAVING count(*) > 1;

If either query returns rows, do not run the migration: resolve each case explicitly
(`finish_sent` with the verified job, `resolve_unknown`, or a manual review that keeps the
history), then re-run the checks. The migration never merges or deletes those rows.

Dropped indexes (`ix_operation_movements_mode`, `ix_operation_movements_dispatch`,
`ix_operation_snapshots_mode`) had no query that used them: every ledger query filters by
`mode` first and the planner picks `ix_operation_movements_review`; `last_snapshot`
orders by `recorded_at` within a mode and now has `ix_operation_snapshots_mode_recorded`.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_guards"
down_revision = "0003_users"
branch_labels = None
depends_on = None

MOVEMENTS = "operation_movements"
EVENTS = "operation_events"
SNAPSHOTS = "operation_snapshots"

INFLIGHT_PREDICATE = "state IN ('queued', 'sending', 'unknown')"
JOB_PREDICATE = "job_id IS NOT NULL"
TRACKED_VEHICLE_KIND_CHECK = "ck_operation_movements_tracked_vehicle_kind"
TRACKED_VEHICLE_KIND_PREDICATE = (
    "tracked_vehicle_kind IS NULL OR tracked_vehicle_kind IN ('machine_device', 'transporter')"
)

APPEND_ONLY_FUNCTION = """
CREATE OR REPLACE FUNCTION operation_events_reject_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'operation_events es append-only: no se actualiza ni se borra el historial'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$
"""
APPEND_ONLY_TRIGGER = """
CREATE TRIGGER operation_events_append_only
BEFORE UPDATE OR DELETE ON operation_events
FOR EACH ROW EXECUTE FUNCTION operation_events_reject_change()
"""


def _postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _partial_unique(name: str, columns: list[str], predicate: str) -> None:
    op.create_index(
        name,
        MOVEMENTS,
        columns,
        unique=True,
        postgresql_where=sa.text(predicate),
        sqlite_where=sa.text(predicate),
    )


def upgrade() -> None:
    if _postgres():
        # Fail fast instead of queueing behind a long transaction; the caller retries.
        op.execute("SET LOCAL lock_timeout = '5s'")

    # operation_movements: identity of the tracked device, unused indexes, SQL guards.
    op.drop_index("ix_operation_movements_mode", table_name=MOVEMENTS)
    op.drop_index("ix_operation_movements_dispatch", table_name=MOVEMENTS)
    with op.batch_alter_table(MOVEMENTS) as batch_op:
        batch_op.add_column(sa.Column("tracked_vehicle_kind", sa.String(16), nullable=True))
        batch_op.create_check_constraint(
            op.f(TRACKED_VEHICLE_KIND_CHECK), TRACKED_VEHICLE_KIND_PREDICATE
        )
    _partial_unique(
        "uq_operation_movements_job_identity", ["mode", "environment", "job_id"], JOB_PREDICATE
    )
    _partial_unique(
        "uq_operation_movements_inflight_machine",
        ["mode", "environment", "machinery_source_id"],
        INFLIGHT_PREDICATE,
    )

    # operation_snapshots: index that serves last_snapshot, and an explicit re-confirmation.
    op.drop_index("ix_operation_snapshots_mode", table_name=SNAPSHOTS)
    op.create_index("ix_operation_snapshots_mode_recorded", SNAPSHOTS, ["mode", "recorded_at"])
    with op.batch_alter_table(SNAPSHOTS) as batch_op:
        batch_op.add_column(
            sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=True)
        )

    # operation_events: who caused the transition (nullable: recorded, never fabricated).
    with op.batch_alter_table(EVENTS) as batch_op:
        batch_op.add_column(sa.Column("actor_user_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("actor_role", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("actor_kind", sa.String(16), nullable=True))

    if _postgres():
        # Row-level trigger: UPDATE and DELETE are rejected; TRUNCATE (test databases)
        # and INSERT are unaffected.
        op.execute(APPEND_ONLY_FUNCTION)
        op.execute("DROP TRIGGER IF EXISTS operation_events_append_only ON operation_events")
        op.execute(APPEND_ONLY_TRIGGER)


def downgrade() -> None:
    """Reverse the schema only; every row and every event stays exactly as it is."""
    if _postgres():
        op.execute("SET LOCAL lock_timeout = '5s'")
        op.execute("DROP TRIGGER IF EXISTS operation_events_append_only ON operation_events")
        op.execute("DROP FUNCTION IF EXISTS operation_events_reject_change()")

    with op.batch_alter_table(EVENTS) as batch_op:
        batch_op.drop_column("actor_kind")
        batch_op.drop_column("actor_role")
        batch_op.drop_column("actor_user_id")

    with op.batch_alter_table(SNAPSHOTS) as batch_op:
        batch_op.drop_column("last_confirmed_at")
    op.drop_index("ix_operation_snapshots_mode_recorded", table_name=SNAPSHOTS)
    op.create_index("ix_operation_snapshots_mode", SNAPSHOTS, ["mode"])

    op.drop_index("uq_operation_movements_inflight_machine", table_name=MOVEMENTS)
    op.drop_index("uq_operation_movements_job_identity", table_name=MOVEMENTS)
    with op.batch_alter_table(MOVEMENTS) as batch_op:
        batch_op.drop_constraint(op.f(TRACKED_VEHICLE_KIND_CHECK), type_="check")
        batch_op.drop_column("tracked_vehicle_kind")
    op.create_index("ix_operation_movements_dispatch", MOVEMENTS, ["state", "created_at"])
    op.create_index("ix_operation_movements_mode", MOVEMENTS, ["mode"])

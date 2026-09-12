"""Persist operation movements, durable dispatch claims and source evidence.

Revision ID: 0001_operations
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_operations"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operation_movements",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False),
        sa.Column("movement_reference", sa.String(255), nullable=False),
        sa.Column("request_source_id", sa.String(255), nullable=False),
        sa.Column("machinery_source_id", sa.String(255), nullable=False),
        sa.Column("project_source_id", sa.String(255), nullable=False),
        sa.Column("tracked_vehicle_id", sa.String(255), nullable=True),
        sa.Column("mapping", sa.JSON(), nullable=False),
        sa.Column("source_request", sa.JSON(), nullable=False),
        sa.Column("source_equipment", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("source_request_hash", sa.String(64), nullable=False),
        sa.Column("source_equipment_hash", sa.String(64), nullable=True),
        sa.Column("identity_hash", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("preparation", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("job_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(255), nullable=True),
        sa.Column("workflow_role", sa.String(255), nullable=True),
        sa.Column("reason_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sending_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("receipt", sa.JSON(none_as_null=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_operation_movements"),
        sa.UniqueConstraint("mode", "environment", "movement_reference", name="movement_identity"),
        sa.CheckConstraint("mode IN ('fixture', 'live')", name="movement_mode"),
        sa.CheckConstraint(
            "state IN ('draft', 'blocked', 'queued', 'sending', 'sent', 'unknown', 'failed')",
            name="movement_state",
        ),
    )
    op.create_index("ix_operation_movements_mode", "operation_movements", ["mode"])
    op.create_index(
        "ix_operation_movements_request_source_id", "operation_movements", ["request_source_id"]
    )
    op.create_index(
        "ix_operation_movements_dispatch", "operation_movements", ["state", "created_at"]
    )
    op.create_table(
        "operation_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("movement_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("state", sa.String(16), nullable=True),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column("evidence_hash", sa.String(64), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(none_as_null=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["movement_id"],
            ["operation_movements.id"],
            name="fk_operation_events_movement_id_operation_movements",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_operation_events"),
        sa.UniqueConstraint("movement_id", "evidence_hash", name="event_evidence_identity"),
    )
    op.create_index("ix_operation_events_movement_id", "operation_events", ["movement_id"])
    op.create_table(
        "operation_snapshots",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_operation_snapshots"),
        sa.CheckConstraint("mode IN ('fixture', 'live')", name="snapshot_mode"),
    )
    op.create_index("ix_operation_snapshots_mode", "operation_snapshots", ["mode"])


def downgrade() -> None:
    op.drop_table("operation_events")
    op.drop_table("operation_snapshots")
    op.drop_table("operation_movements")

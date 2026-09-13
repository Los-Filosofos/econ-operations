"""Add next_review_at and review index to operation_movements.

Revision ID: 0002_review_schedule
Revises: 0001_operations
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_review_schedule"
down_revision = "0001_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("operation_movements") as batch_op:
        batch_op.add_column(
            sa.Column(
                "next_review_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.create_index(
            "ix_operation_movements_review",
            ["mode", "state", "next_review_at"],
        )


def downgrade() -> None:
    with op.batch_alter_table("operation_movements") as batch_op:
        batch_op.drop_index("ix_operation_movements_review")
        batch_op.drop_column("next_review_at")

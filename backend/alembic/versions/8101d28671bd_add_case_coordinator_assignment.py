
"""add case coordinator assignment

Revision ID: 8101d28671bd
Revises: 68a1a0c11918
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8101d28671bd"
down_revision: Union[str, Sequence[str], None] = "68a1a0c11918"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("assigned_coordinator_id", sa.Integer(), nullable=True),
    )

    op.create_index(
        "ix_cases_assigned_coordinator_id",
        "cases",
        ["assigned_coordinator_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_cases_assigned_coordinator_id_users",
        "cases",
        "users",
        ["assigned_coordinator_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_cases_assigned_coordinator_id_users",
        "cases",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_cases_assigned_coordinator_id",
        table_name="cases",
    )

    op.drop_column("cases", "assigned_coordinator_id")

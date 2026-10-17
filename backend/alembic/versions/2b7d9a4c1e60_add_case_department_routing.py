
"""Add department routing to cases.

Revision ID: 2b7d9a4c1e60
Revises: 1a66b00b6369
"""

from alembic import op
import sqlalchemy as sa


revision = "2b7d9a4c1e60"
down_revision = "1a66b00b6369"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cases",
        sa.Column("department", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_cases_department",
        "cases",
        ["department"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cases_department", table_name="cases")
    op.drop_column("cases", "department")

"""Add phone numbers to user and pending registration records.

Revision ID: 7f4a2c9e1d30
Revises: c41e8a72f90b
"""

from alembic import op
import sqlalchemy as sa


revision = "7f4a2c9e1d30"
down_revision = "c41e8a72f90b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=16), nullable=True))
    op.add_column(
        "pending_email_verifications",
        sa.Column("phone", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pending_email_verifications", "phone")
    op.drop_column("users", "phone")

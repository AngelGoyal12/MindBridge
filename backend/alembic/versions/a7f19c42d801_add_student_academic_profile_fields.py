"""Add student department/course and semester profile fields.

Revision ID: a7f19c42d801
Revises: 1a66b00b6369, 3d6b2f9a8c41
"""

from alembic import op
import sqlalchemy as sa


revision = "a7f19c42d801"
down_revision = ("1a66b00b6369", "3d6b2f9a8c41")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("department_course", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("current_semester", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pending_email_verifications",
        sa.Column("department_course", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "pending_email_verifications",
        sa.Column("current_semester", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pending_email_verifications", "current_semester")
    op.drop_column("pending_email_verifications", "department_course")
    op.drop_column("users", "current_semester")
    op.drop_column("users", "department_course")

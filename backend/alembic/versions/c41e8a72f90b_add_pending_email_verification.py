"""Add pending student email verification records.

Revision ID: c41e8a72f90b
Revises: 2b7d9a4c1e60
"""

from alembic import op
import sqlalchemy as sa


revision = "c41e8a72f90b"
down_revision = "2b7d9a4c1e60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pending_email_verifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("otp_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("resend_count", sa.Integer(), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(
        "ix_pending_email_verifications_id",
        "pending_email_verifications",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_pending_email_verifications_expires_at",
        "pending_email_verifications",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pending_email_verifications_expires_at",
        table_name="pending_email_verifications",
    )
    op.drop_index(
        "ix_pending_email_verifications_id",
        table_name="pending_email_verifications",
    )
    op.drop_table("pending_email_verifications")

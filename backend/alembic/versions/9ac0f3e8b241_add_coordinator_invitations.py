"""add hashed single-use coordinator invitations

Revision ID: 9ac0f3e8b241
Revises: 7f4a2c9e1d30
"""

from alembic import op
import sqlalchemy as sa


revision = "9ac0f3e8b241"
down_revision = "7f4a2c9e1d30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coordinator_invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_coordinator_invitations_case_id_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            ["users.id"],
            name="fk_coordinator_invitations_invited_by_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coordinator_invitations_id",
        "coordinator_invitations",
        ["id"],
    )
    op.create_index(
        "ix_coordinator_invitations_case_id",
        "coordinator_invitations",
        ["case_id"],
    )
    op.create_index(
        "ix_coordinator_invitations_invited_by_user_id",
        "coordinator_invitations",
        ["invited_by_user_id"],
    )
    op.create_index(
        "ix_coordinator_invitations_email",
        "coordinator_invitations",
        ["email"],
    )
    op.create_index(
        "ix_coordinator_invitations_token_hash",
        "coordinator_invitations",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_coordinator_invitations_expires_at",
        "coordinator_invitations",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_coordinator_invitations_expires_at",
        table_name="coordinator_invitations",
    )
    op.drop_index(
        "ix_coordinator_invitations_token_hash",
        table_name="coordinator_invitations",
    )
    op.drop_index(
        "ix_coordinator_invitations_email",
        table_name="coordinator_invitations",
    )
    op.drop_index(
        "ix_coordinator_invitations_invited_by_user_id",
        table_name="coordinator_invitations",
    )
    op.drop_index(
        "ix_coordinator_invitations_case_id",
        table_name="coordinator_invitations",
    )
    op.drop_index(
        "ix_coordinator_invitations_id",
        table_name="coordinator_invitations",
    )
    op.drop_table("coordinator_invitations")

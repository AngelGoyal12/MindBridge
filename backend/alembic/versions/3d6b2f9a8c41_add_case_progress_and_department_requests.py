"""add case progress and department action requests

Revision ID: 3d6b2f9a8c41
Revises: 9ac0f3e8b241
"""

from alembic import op
import sqlalchemy as sa


revision = "3d6b2f9a8c41"
down_revision = "9ac0f3e8b241"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_progress_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=False),
        sa.Column("update_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_case_progress_updates_case_id_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            name="fk_case_progress_updates_author_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_case_progress_updates_id", "case_progress_updates", ["id"]
    )
    op.create_index(
        "ix_case_progress_updates_case_id",
        "case_progress_updates",
        ["case_id"],
    )
    op.create_index(
        "ix_case_progress_updates_author_user_id",
        "case_progress_updates",
        ["author_user_id"],
    )

    op.create_table(
        "department_action_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("coordinator_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("request_type", sa.String(length=30), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_department_action_requests_case_id_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["coordinator_id"],
            ["users.id"],
            name="fk_department_action_requests_coordinator_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["users.id"],
            name="fk_department_action_requests_sender_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_department_action_requests_id",
        "department_action_requests",
        ["id"],
    )
    op.create_index(
        "ix_department_action_requests_case_id",
        "department_action_requests",
        ["case_id"],
    )
    op.create_index(
        "ix_department_action_requests_coordinator_id",
        "department_action_requests",
        ["coordinator_id"],
    )
    op.create_index(
        "ix_department_action_requests_sender_user_id",
        "department_action_requests",
        ["sender_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_department_action_requests_sender_user_id",
        table_name="department_action_requests",
    )
    op.drop_index(
        "ix_department_action_requests_coordinator_id",
        table_name="department_action_requests",
    )
    op.drop_index(
        "ix_department_action_requests_case_id",
        table_name="department_action_requests",
    )
    op.drop_index(
        "ix_department_action_requests_id",
        table_name="department_action_requests",
    )
    op.drop_table("department_action_requests")

    op.drop_index(
        "ix_case_progress_updates_author_user_id",
        table_name="case_progress_updates",
    )
    op.drop_index(
        "ix_case_progress_updates_case_id",
        table_name="case_progress_updates",
    )
    op.drop_index(
        "ix_case_progress_updates_id",
        table_name="case_progress_updates",
    )
    op.drop_table("case_progress_updates")

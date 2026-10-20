"""add department tasks and task events

Revision ID: e5b2c7d1a904
Revises: a7f19c42d801
"""

from alembic import op
import sqlalchemy as sa


revision = "e5b2c7d1a904"
down_revision = "a7f19c42d801"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "department_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=20),
            server_default="normal",
            nullable=False,
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="assigned",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("completion_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_department_tasks_case_id_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"],
            ["users.id"],
            name="fk_department_tasks_assigned_by_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_user_id"],
            ["users.id"],
            name="fk_department_tasks_completed_by_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_department_tasks_id", "department_tasks", ["id"])
    op.create_index(
        "ix_department_tasks_case_id", "department_tasks", ["case_id"]
    )
    op.create_index(
        "ix_department_tasks_department", "department_tasks", ["department"]
    )
    op.create_index(
        "ix_department_tasks_assigned_by_user_id",
        "department_tasks",
        ["assigned_by_user_id"],
    )
    op.create_index(
        "ix_department_tasks_status", "department_tasks", ["status"]
    )

    op.create_table(
        "department_task_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["department_tasks.id"],
            name="fk_department_task_events_task_id_department_tasks",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_department_task_events_actor_user_id_users",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_department_task_events_id", "department_task_events", ["id"]
    )
    op.create_index(
        "ix_department_task_events_task_id",
        "department_task_events",
        ["task_id"],
    )
    op.create_index(
        "ix_department_task_events_actor_user_id",
        "department_task_events",
        ["actor_user_id"],
    )


def downgrade() -> None:
    op.drop_table("department_task_events")
    op.drop_table("department_tasks")

"""add task staff assignment and internal messages

Revision ID: f7c3d9e2b615
Revises: e5b2c7d1a904
"""

from alembic import op
import sqlalchemy as sa


revision = "f7c3d9e2b615"
down_revision = "e5b2c7d1a904"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "department_tasks",
        sa.Column("assigned_staff_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "department_tasks",
        sa.Column("assigned_staff_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_department_tasks_assigned_staff_id",
        "department_tasks",
        ["assigned_staff_id"],
    )
    op.create_foreign_key(
        "fk_department_tasks_assigned_staff_id_users",
        "department_tasks",
        "users",
        ["assigned_staff_id"],
        ["id"],
    )

    op.create_table(
        "internal_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("audience_label", sa.String(length=150), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("subject", sa.String(length=150), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["users.id"],
            name="fk_internal_messages_sender_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            name="fk_internal_messages_recipient_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_internal_messages_case_id_cases",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_internal_messages_id", "internal_messages", ["id"])
    op.create_index("ix_internal_messages_group_id", "internal_messages", ["group_id"])
    op.create_index(
        "ix_internal_messages_sender_user_id", "internal_messages", ["sender_user_id"]
    )
    op.create_index(
        "ix_internal_messages_recipient_user_id",
        "internal_messages",
        ["recipient_user_id"],
    )
    op.create_index("ix_internal_messages_case_id", "internal_messages", ["case_id"])


def downgrade() -> None:
    op.drop_table("internal_messages")
    op.drop_constraint(
        "fk_department_tasks_assigned_staff_id_users",
        "department_tasks",
        type_="foreignkey",
    )
    op.drop_index("ix_department_tasks_assigned_staff_id", table_name="department_tasks")
    op.drop_column("department_tasks", "assigned_staff_at")
    op.drop_column("department_tasks", "assigned_staff_id")

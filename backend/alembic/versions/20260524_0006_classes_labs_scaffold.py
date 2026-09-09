"""classes/labs scaffold

Revision ID: 20260524_0006
Revises: 20260524_0005
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "20260524_0006"
down_revision = "20260524_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("term", sa.String(length=120), nullable=True),
        sa.Column("instructor_id", sa.Integer(), nullable=True),
        sa.Column("join_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["instructor_id"], ["users.id"]),
        sa.UniqueConstraint("name", name="uq_classes_name"),
    )
    op.create_index("ix_classes_instructor_id", "classes", ["instructor_id"])

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("class_id", "user_id", name="uq_enrollments_class_user"),
    )
    op.create_index("ix_enrollments_class_id", "enrollments", ["class_id"])
    op.create_index("ix_enrollments_user_id", "enrollments", ["user_id"])

    op.create_table(
        "labs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("default_pool_id", sa.Integer(), nullable=False),
        sa.Column(
            "student_can_reset",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "student_can_power_off",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "terminal_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "console_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "rdp_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_pool_id"], ["desktop_pools.id"]),
    )
    op.create_index("ix_labs_class_id", "labs", ["class_id"])
    op.create_index("ix_labs_default_pool_id", "labs", ["default_pool_id"])


def downgrade() -> None:
    op.drop_index("ix_labs_default_pool_id", table_name="labs")
    op.drop_index("ix_labs_class_id", table_name="labs")
    op.drop_table("labs")
    op.drop_index("ix_enrollments_user_id", table_name="enrollments")
    op.drop_index("ix_enrollments_class_id", table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_index("ix_classes_instructor_id", table_name="classes")
    op.drop_table("classes")

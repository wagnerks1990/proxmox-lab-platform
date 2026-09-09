"""pilot bootstrap and durable operations

Revision ID: 20260908_0014
Revises: 20260908_0013
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260908_0014"
down_revision = "20260908_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Roles are application reference data. Seeding them here makes a clean
    # database capable of completing the one-time administrator enrollment.
    op.execute(
        "INSERT INTO roles (name) VALUES ('Student'), ('Teacher'), ('Admin') ON CONFLICT (name) DO NOTHING"
    )
    op.add_column(
        "deployment_update_runs",
        sa.Column("agent_operation_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_deployment_update_runs_agent_operation_id",
        "deployment_update_runs",
        ["agent_operation_id"],
    )
    op.create_table(
        "vmid_allocators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False, server_default="200000"),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope"),
    )
    op.create_index(
        "ix_vmid_allocators_scope", "vmid_allocators", ["scope"], unique=True
    )
    op.execute(
        "INSERT INTO vmid_allocators (scope, next_value) VALUES ('proxmox-cluster', 200000)"
    )

    op.create_table(
        "durable_operations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("requested_by", sa.Integer(), nullable=True),
        sa.Column("operation_type", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column(
            "state", sa.String(length=32), nullable=False, server_default="queued"
        ),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("proxmox_upid", sa.String(length=255), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("run_after", sa.DateTime(), nullable=True),
        sa.Column("error", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_durable_operations_state",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_durable_operations_idempotency_key"
        ),
    )
    for column in (
        "organization_id",
        "requested_by",
        "operation_type",
        "state",
        "lease_owner",
        "lease_expires_at",
        "run_after",
        "created_at",
    ):
        op.create_index(
            f"ix_durable_operations_{column}", "durable_operations", [column]
        )
    op.create_unique_constraint("uq_student_vms_vmid", "student_vms", ["vmid"])


def downgrade() -> None:
    op.drop_constraint("uq_student_vms_vmid", "student_vms", type_="unique")
    for column in reversed(
        (
            "organization_id",
            "requested_by",
            "operation_type",
            "state",
            "lease_owner",
            "lease_expires_at",
            "run_after",
            "created_at",
        )
    ):
        op.drop_index(
            f"ix_durable_operations_{column}", table_name="durable_operations"
        )
    op.drop_table("durable_operations")
    op.drop_index("ix_vmid_allocators_scope", table_name="vmid_allocators")
    op.drop_table("vmid_allocators")
    op.drop_index(
        "ix_deployment_update_runs_agent_operation_id",
        table_name="deployment_update_runs",
    )
    op.drop_column("deployment_update_runs", "agent_operation_id")

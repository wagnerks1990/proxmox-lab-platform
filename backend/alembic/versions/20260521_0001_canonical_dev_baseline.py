"""canonical development baseline

Revision ID: 20260521_0001
Revises:
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260521_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")
        ),
        sa.Column(
            "force_password_change",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")
        ),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_users_role_id_roles"
        ),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "vm_templates",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("proxmox_node", sa.String(length=50), nullable=False),
        sa.Column("source_vmid", sa.Integer(), nullable=False),
        sa.Column(
            "enabled", sa.Boolean(), nullable=True, server_default=sa.text("true")
        ),
        sa.UniqueConstraint("name", name="uq_vm_templates_name"),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_permissions_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["vm_templates.id"],
            name="fk_permissions_template_id_vm_templates",
        ),
    )

    op.create_table(
        "student_vms",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("vm_name", sa.String(length=100), nullable=False),
        sa.Column("vmid", sa.Integer(), nullable=False),
        sa.Column("proxmox_node", sa.String(length=50), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=True, server_default="provisioning"
        ),
        sa.Column("operating_system", sa.String(length=50), nullable=True),
        sa.Column("access_protocols", sa.String(length=255), nullable=True),
        sa.Column(
            "ssh_enabled", sa.Boolean(), nullable=True, server_default=sa.text("true")
        ),
        sa.Column(
            "rdp_enabled", sa.Boolean(), nullable=True, server_default=sa.text("false")
        ),
        sa.Column(
            "spice_enabled",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "console_enabled",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("true"),
        ),
        sa.Column("default_username", sa.String(length=100), nullable=True),
        sa.Column("assigned_ip", sa.String(length=64), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("ssh_username", sa.String(length=100), nullable=True),
        sa.Column("ssh_auth_method", sa.String(length=50), nullable=True),
        sa.Column("ssh_port", sa.Integer(), nullable=True, server_default="22"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_student_vms_owner_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["vm_templates.id"],
            name="fk_student_vms_template_id_vm_templates",
        ),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_audit_logs_actor_id_users"
        ),
    )

    op.create_table(
        "connection_launches",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("vm_id", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=50), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="success"
        ),
        sa.Column("details", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_connection_launches_actor_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["vm_id"],
            ["student_vms.id"],
            name="fk_connection_launches_vm_id_student_vms",
        ),
    )

    op.create_table(
        "desktop_pools",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("pool_type", sa.String(length=32), nullable=False),
        sa.Column("template_vmid", sa.Integer(), nullable=True),
        sa.Column("template_node", sa.String(length=50), nullable=True),
        sa.Column("default_protocol", sa.String(length=50), nullable=False),
        sa.Column("target_node", sa.String(length=50), nullable=True),
        sa.Column("storage", sa.String(length=100), nullable=True),
        sa.Column("bridge", sa.String(length=100), nullable=True),
        sa.Column("vlan_tag", sa.Integer(), nullable=True),
        sa.Column("vmid_start", sa.Integer(), nullable=True),
        sa.Column("vmid_end", sa.Integer(), nullable=True),
        sa.Column("naming_pattern", sa.String(length=100), nullable=True),
        sa.Column("desired_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "maintenance_mode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )

    op.create_index("ix_desktop_pools_name", "desktop_pools", ["name"], unique=True)
    op.create_index(
        "ix_desktop_pools_pool_type", "desktop_pools", ["pool_type"], unique=False
    )
    op.create_index(
        "ix_desktop_pools_maintenance_mode",
        "desktop_pools",
        ["maintenance_mode"],
        unique=False,
    )
    op.create_index(
        "ix_desktop_pools_enabled", "desktop_pools", ["enabled"], unique=False
    )

    op.create_table(
        "vm_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("vm_id", sa.Integer(), nullable=False),
        sa.Column("pool_id", sa.Integer(), nullable=True),
        sa.Column("connection_launch_id", sa.Integer(), nullable=True),
        sa.Column("protocol", sa.String(length=50), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("node", sa.String(length=50), nullable=True),
        sa.Column("proxmox_vmid", sa.Integer(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("launched_at", sa.DateTime(), nullable=True),
        sa.Column("disconnected_at", sa.DateTime(), nullable=True),
        sa.Column("expired_at", sa.DateTime(), nullable=True),
        sa.Column("failed_at", sa.DateTime(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_vm_sessions_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["vm_id"], ["student_vms.id"], name="fk_vm_sessions_vm_id_student_vms"
        ),
        sa.ForeignKeyConstraint(
            ["connection_launch_id"],
            ["connection_launches.id"],
            name="fk_vm_sessions_connection_launch_id_connection_launches",
        ),
    )

    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "severity", sa.String(length=20), nullable=False, server_default="info"
        ),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("vm_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
    )
    op.create_index(
        "ix_telemetry_events_event_type", "telemetry_events", ["event_type"]
    )
    op.create_index("ix_telemetry_events_severity", "telemetry_events", ["severity"])
    op.create_index("ix_telemetry_events_user_id", "telemetry_events", ["user_id"])
    op.create_index("ix_telemetry_events_vm_id", "telemetry_events", ["vm_id"])
    op.create_index(
        "ix_telemetry_events_session_id", "telemetry_events", ["session_id"]
    )
    op.create_index(
        "ix_telemetry_events_request_id", "telemetry_events", ["request_id"]
    )
    op.create_index(
        "ix_telemetry_events_created_at", "telemetry_events", ["created_at"]
    )

    op.create_table(
        "worker_runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("worker_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("summary_json", sa.Text(), nullable=True),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_worker_runs_worker_name", "worker_runs", ["worker_name"])
    op.create_index("ix_worker_runs_status", "worker_runs", ["status"])
    op.create_index("ix_worker_runs_started_at", "worker_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_worker_runs_started_at", table_name="worker_runs")
    op.drop_index("ix_worker_runs_status", table_name="worker_runs")
    op.drop_index("ix_worker_runs_worker_name", table_name="worker_runs")
    op.drop_table("worker_runs")

    op.drop_index("ix_telemetry_events_created_at", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_request_id", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_session_id", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_vm_id", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_user_id", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_severity", table_name="telemetry_events")
    op.drop_index("ix_telemetry_events_event_type", table_name="telemetry_events")
    op.drop_table("telemetry_events")

    op.drop_table("vm_sessions")

    op.drop_index("ix_desktop_pools_enabled", table_name="desktop_pools")
    op.drop_index("ix_desktop_pools_maintenance_mode", table_name="desktop_pools")
    op.drop_index("ix_desktop_pools_pool_type", table_name="desktop_pools")
    op.drop_index("ix_desktop_pools_name", table_name="desktop_pools")
    op.drop_table("desktop_pools")

    op.drop_table("connection_launches")
    op.drop_table("audit_logs")
    op.drop_table("student_vms")
    op.drop_table("permissions")
    op.drop_table("vm_templates")
    op.drop_table("users")
    op.drop_table("roles")

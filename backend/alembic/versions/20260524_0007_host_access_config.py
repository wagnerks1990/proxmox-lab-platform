"""host access config

Revision ID: 20260524_0007
Revises: 20260524_0006
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "20260524_0007"
down_revision = "20260524_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proxmox_host_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("node_name", sa.String(length=120), nullable=False),
        sa.Column(
            "runner_user",
            sa.String(length=120),
            nullable=False,
            server_default="labgoblin-runner",
        ),
        sa.Column(
            "auth_method",
            sa.String(length=32),
            nullable=False,
            server_default="ssh_key",
        ),
        sa.Column("encrypted_private_key", sa.String(), nullable=True),
        sa.Column("key_ref", sa.String(length=255), nullable=True),
        sa.Column("public_key_fingerprint", sa.String(length=255), nullable=True),
        sa.Column("capabilities_json", sa.String(), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="api_only"
        ),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["cluster_id"], ["proxmox_clusters.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "cluster_id", "node_name", name="uq_host_access_cluster_node"
        ),
    )


def downgrade() -> None:
    op.drop_table("proxmox_host_access")

"""bind VMs to clusters and preserve deletion history

Revision ID: 20260908_0015
Revises: 20260908_0014
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260908_0015"
down_revision = "20260908_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Older databases could contain several active rows. Keep the newest one
    # deterministically before enforcing the invariant at the database layer.
    op.execute(
        """
        UPDATE proxmox_clusters
        SET is_active = false
        WHERE is_active = true
          AND id <> (SELECT max(id) FROM proxmox_clusters WHERE is_active = true)
        """
    )
    op.create_index(
        "uq_proxmox_clusters_single_active",
        "proxmox_clusters",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.add_column(
        "vm_templates", sa.Column("proxmox_cluster_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_vm_templates_proxmox_cluster_id",
        "vm_templates",
        "proxmox_clusters",
        ["proxmox_cluster_id"],
        ["id"],
    )
    op.create_index(
        "ix_vm_templates_proxmox_cluster_id", "vm_templates", ["proxmox_cluster_id"]
    )
    op.execute(
        """
        UPDATE vm_templates
        SET proxmox_cluster_id = (SELECT id FROM proxmox_clusters WHERE is_active = true)
        WHERE proxmox_cluster_id IS NULL
        """
    )

    op.add_column(
        "student_vms", sa.Column("proxmox_cluster_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_student_vms_proxmox_cluster_id",
        "student_vms",
        "proxmox_clusters",
        ["proxmox_cluster_id"],
        ["id"],
    )
    op.create_index(
        "ix_student_vms_proxmox_cluster_id", "student_vms", ["proxmox_cluster_id"]
    )
    op.execute(
        """
        UPDATE student_vms
        SET proxmox_cluster_id = COALESCE(
            (SELECT proxmox_cluster_id FROM vm_templates WHERE vm_templates.id = student_vms.template_id),
            (SELECT id FROM proxmox_clusters WHERE is_active = true)
        )
        WHERE proxmox_cluster_id IS NULL
        """
    )
    op.add_column("student_vms", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_student_vms_deleted_at", "student_vms", ["deleted_at"])

    op.add_column(
        "asset_sync_jobs",
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "asset_sync_jobs", sa.Column("lease_expires_at", sa.DateTime(), nullable=True)
    )
    op.create_index(
        "ix_asset_sync_jobs_lease_owner", "asset_sync_jobs", ["lease_owner"]
    )
    op.create_index(
        "ix_asset_sync_jobs_lease_expires_at", "asset_sync_jobs", ["lease_expires_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_asset_sync_jobs_lease_expires_at", table_name="asset_sync_jobs")
    op.drop_index("ix_asset_sync_jobs_lease_owner", table_name="asset_sync_jobs")
    op.drop_column("asset_sync_jobs", "lease_expires_at")
    op.drop_column("asset_sync_jobs", "lease_owner")

    op.drop_index("ix_student_vms_deleted_at", table_name="student_vms")
    op.drop_column("student_vms", "deleted_at")
    op.drop_index("ix_student_vms_proxmox_cluster_id", table_name="student_vms")
    op.drop_constraint(
        "fk_student_vms_proxmox_cluster_id", "student_vms", type_="foreignkey"
    )
    op.drop_column("student_vms", "proxmox_cluster_id")

    op.drop_index("ix_vm_templates_proxmox_cluster_id", table_name="vm_templates")
    op.drop_constraint(
        "fk_vm_templates_proxmox_cluster_id", "vm_templates", type_="foreignkey"
    )
    op.drop_column("vm_templates", "proxmox_cluster_id")
    op.drop_index("uq_proxmox_clusters_single_active", table_name="proxmox_clusters")

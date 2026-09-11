"""enforce permission and cluster VMID uniqueness

Revision ID: 20260911_0016
Revises: 20260908_0015
Create Date: 2026-09-11
"""

from alembic import op


revision = "20260911_0016"
down_revision = "20260908_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve the oldest row for each direct permission before enforcing the
    # idempotent application-level contract.
    op.execute(
        """
        DELETE FROM permissions duplicate
        USING permissions canonical
        WHERE duplicate.user_id = canonical.user_id
          AND duplicate.template_id = canonical.template_id
          AND duplicate.id > canonical.id
        """
    )
    op.create_unique_constraint(
        "uq_permissions_user_template",
        "permissions",
        ["user_id", "template_id"],
    )

    # Fail before altering constraints if a drifted database contains a
    # same-cluster collision. The exception leaves the migration transaction
    # and the existing global constraint intact.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM student_vms
                WHERE proxmox_cluster_id IS NOT NULL
                GROUP BY proxmox_cluster_id, vmid
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot enforce per-cluster VMID uniqueness: duplicate (proxmox_cluster_id, vmid) rows exist';
            END IF;
        END $$
        """
    )
    op.drop_constraint("uq_student_vms_vmid", "student_vms", type_="unique")
    op.create_unique_constraint(
        "uq_student_vms_cluster_vmid",
        "student_vms",
        ["proxmox_cluster_id", "vmid"],
    )


def downgrade() -> None:
    # Restoring global uniqueness is unsafe once separate clusters reuse a
    # VMID. Stop with an actionable error before changing either constraint.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM student_vms
                GROUP BY vmid
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot restore global VMID uniqueness: VMIDs are reused across clusters';
            END IF;
        END $$
        """
    )
    op.drop_constraint("uq_student_vms_cluster_vmid", "student_vms", type_="unique")
    op.create_unique_constraint("uq_student_vms_vmid", "student_vms", ["vmid"])
    op.drop_constraint("uq_permissions_user_template", "permissions", type_="unique")

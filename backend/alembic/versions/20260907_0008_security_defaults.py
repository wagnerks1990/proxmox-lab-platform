"""security defaults and canonical role compatibility

Revision ID: 20260907_0008
Revises: 20260524_0007
Create Date: 2026-09-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260907_0008"
down_revision = "20260524_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep the compatibility role column synchronized while V2 removes it.
    op.execute(
        """
        UPDATE users
           SET role = roles.name
          FROM roles
         WHERE users.role_id = roles.id
           AND users.role IS DISTINCT FROM roles.name
        """
    )
    op.alter_column(
        "proxmox_clusters",
        "verify_ssl",
        existing_type=sa.Boolean(),
        server_default=sa.true(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "proxmox_clusters",
        "verify_ssl",
        existing_type=sa.Boolean(),
        server_default=sa.false(),
        existing_nullable=False,
    )

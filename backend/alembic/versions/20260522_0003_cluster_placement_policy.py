"""add placement policy to proxmox cluster defaults

Revision ID: 20260522_0003
Revises: 20260522_0002
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa


revision = '20260522_0003'
down_revision = '20260522_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('proxmox_cluster_defaults', sa.Column('placement_policy', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('proxmox_cluster_defaults', 'placement_policy')

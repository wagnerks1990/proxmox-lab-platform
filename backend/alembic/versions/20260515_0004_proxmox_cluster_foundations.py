"""proxmox cluster-aware foundations

Revision ID: 20260515_0004
Revises: 20260515_0003
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260515_0004'
down_revision = '20260515_0003'
branch_labels = None
depends_on = None

def _has_table(bind, name):
    return inspect(bind).has_table(name)

def _has_column(bind, table, col):
    return any(c['name'] == col for c in inspect(bind).get_columns(table))

def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, 'proxmox_clusters'):
        op.create_table('proxmox_clusters',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=100), unique=True, nullable=False),
            sa.Column('api_url', sa.String(length=255), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )

    if not _has_table(bind, 'proxmox_nodes'):
        op.create_table('proxmox_nodes',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('cluster_id', sa.Integer(), sa.ForeignKey('proxmox_clusters.id'), nullable=False),
            sa.Column('node_name', sa.String(length=100), nullable=False),
            sa.Column('management_ip', sa.String(length=64), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('last_seen', sa.DateTime(), nullable=True),
            sa.Column('cpu_usage', sa.String(length=50), nullable=True),
            sa.Column('memory_usage', sa.String(length=50), nullable=True),
            sa.Column('storage_summary', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )

    if _has_table(bind, 'vm_pools'):
        adds = [
            ('cluster_id', sa.Integer(), sa.ForeignKey('proxmox_clusters.id')),
            ('node_id', sa.Integer(), sa.ForeignKey('proxmox_nodes.id')),
            ('storage_pool', sa.String(length=100), None),
            ('network_bridge', sa.String(length=100), None),
            ('placement_strategy', sa.String(length=50), None),
            ('preferred_node_id', sa.Integer(), sa.ForeignKey('proxmox_nodes.id')),
            ('resource_pool_id', sa.Integer(), sa.ForeignKey('vm_pools.id')),
        ]
        for name, typ, fk in adds:
            if not _has_column(bind, 'vm_pools', name):
                if fk is None:
                    op.add_column('vm_pools', sa.Column(name, typ, nullable=True))
                else:
                    op.add_column('vm_pools', sa.Column(name, typ, nullable=True))

def downgrade() -> None:
    pass

"""desktop pools and vdi admin expansion

Revision ID: 20260516_0006
Revises: 20260515_0005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260516_0006'
down_revision = '20260515_0005'
branch_labels = None
depends_on = None

def _has_table(bind, name):
    return inspect(bind).has_table(name)

def _has_column(bind, table, col):
    return any(c['name'] == col for c in inspect(bind).get_columns(table))

def _add(table, col):
    b = op.get_bind()
    if not _has_column(b, table, col.name):
        op.add_column(table, col)

def upgrade() -> None:
    b = op.get_bind()
    if not _has_table(b, 'desktop_pools'):
        op.create_table('desktop_pools',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(100), unique=True, nullable=False),
            sa.Column('description', sa.String(255), nullable=True),
            sa.Column('pool_type', sa.String(20), nullable=False, server_default='lab'),
            sa.Column('template_id', sa.Integer(), sa.ForeignKey('vm_templates.id'), nullable=True),
            sa.Column('resource_pool_id', sa.Integer(), sa.ForeignKey('vm_pools.id'), nullable=True),
            sa.Column('cluster_id', sa.Integer(), sa.ForeignKey('proxmox_clusters.id'), nullable=True),
            sa.Column('node_id', sa.Integer(), sa.ForeignKey('proxmox_nodes.id'), nullable=True),
            sa.Column('storage_pool', sa.String(100), nullable=True),
            sa.Column('network_bridge', sa.String(100), nullable=True),
            sa.Column('min_ready', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('max_desktops', sa.Integer(), nullable=False, server_default='20'),
            sa.Column('auto_start', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('auto_recycle', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('naming_prefix', sa.String(50), nullable=True),
            sa.Column('assignment_mode', sa.String(20), nullable=False, server_default='manual'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )
    if _has_table(b, 'vm_pools'):
        _add('vm_pools', sa.Column('cpu_limit', sa.String(50), nullable=True))
        _add('vm_pools', sa.Column('memory_limit_mb', sa.Integer(), nullable=True))
        _add('vm_pools', sa.Column('allowed_roles', sa.String(255), nullable=True))

def downgrade() -> None:
    pass

"""schema drift cleanup for connection launches, templates, and user role compatibility

Revision ID: 20260515_0005
Revises: 20260515_0004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = '20260515_0005'
down_revision = '20260515_0004'
branch_labels = None
depends_on = None


def _has_table(bind, name):
    return inspect(bind).has_table(name)


def _has_column(bind, table, col):
    return any(c['name'] == col for c in inspect(bind).get_columns(table))


def _safe_add_column(table, column):
    bind = op.get_bind()
    if not _has_column(bind, table, column.name):
        op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, 'connection_launches'):
        _safe_add_column('connection_launches', sa.Column('actor_id', sa.Integer(), nullable=True))
        _safe_add_column('connection_launches', sa.Column('vm_id', sa.Integer(), nullable=True))
        _safe_add_column('connection_launches', sa.Column('protocol', sa.String(length=50), nullable=True))
        _safe_add_column('connection_launches', sa.Column('status', sa.String(length=20), nullable=True))
        _safe_add_column('connection_launches', sa.Column('details', sa.String(length=255), nullable=True))
        _safe_add_column('connection_launches', sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()))

        # backfill actor_id if legacy user_id exists
        if _has_column(bind, 'connection_launches', 'user_id') and _has_column(bind, 'connection_launches', 'actor_id'):
            bind.execute(text('UPDATE connection_launches SET actor_id = COALESCE(actor_id, user_id)'))

    if _has_table(bind, 'vm_templates'):
        _safe_add_column('vm_templates', sa.Column('operating_system', sa.String(length=50), nullable=True))
        _safe_add_column('vm_templates', sa.Column('default_protocol', sa.String(length=255), nullable=True))
        _safe_add_column('vm_templates', sa.Column('default_protocols', sa.String(length=255), nullable=True))
        _safe_add_column('vm_templates', sa.Column('description', sa.String(length=255), nullable=True))
        _safe_add_column('vm_templates', sa.Column('cluster_id', sa.Integer(), nullable=True))
        _safe_add_column('vm_templates', sa.Column('node_id', sa.Integer(), nullable=True))
        _safe_add_column('vm_templates', sa.Column('storage_pool', sa.String(length=100), nullable=True))
        _safe_add_column('vm_templates', sa.Column('network_bridge', sa.String(length=100), nullable=True))
        _safe_add_column('vm_templates', sa.Column('spice_enabled', sa.Boolean(), nullable=True, server_default=sa.text('false')))
        _safe_add_column('vm_templates', sa.Column('rdp_enabled', sa.Boolean(), nullable=True, server_default=sa.text('false')))
        _safe_add_column('vm_templates', sa.Column('web_terminal_enabled', sa.Boolean(), nullable=True, server_default=sa.text('true')))
        _safe_add_column('vm_templates', sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')))
        _safe_add_column('vm_templates', sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()))

    if _has_table(bind, 'users') and not _has_column(bind, 'users', 'role'):
        _safe_add_column('users', sa.Column('role', sa.String(length=50), nullable=True))


def downgrade() -> None:
    pass

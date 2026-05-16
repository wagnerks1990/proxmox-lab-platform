"""deskpool foundations: pools groups protocol settings template metadata

Revision ID: 20260515_0003
Revises: 20260515_0002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260515_0003'
down_revision = '20260515_0002'
branch_labels = None
depends_on = None


def _has_table(bind, name):
    return inspect(bind).has_table(name)


def _has_column(bind, table, col):
    return any(c['name'] == col for c in inspect(bind).get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, 'vm_templates'):
        for col, typ in [
            ('operating_system', sa.String(length=50)),
            ('default_protocols', sa.String(length=255)),
            ('description', sa.String(length=255)),
        ]:
            if not _has_column(bind, 'vm_templates', col):
                op.add_column('vm_templates', sa.Column(col, typ, nullable=True))

    if not _has_table(bind, 'vm_pools'):
        op.create_table('vm_pools',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=100), unique=True, nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('default_template_id', sa.Integer(), sa.ForeignKey('vm_templates.id'), nullable=True),
            sa.Column('max_vms', sa.Integer(), nullable=False, server_default='20'),
            sa.Column('max_running_vms', sa.Integer(), nullable=False, server_default='10'),
            sa.Column('auto_start', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('recycle_on_logout', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )

    if not _has_table(bind, 'lab_groups'):
        op.create_table('lab_groups',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=100), unique=True, nullable=False),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )

    if not _has_table(bind, 'lab_group_members'):
        op.create_table('lab_group_members',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('group_id', sa.Integer(), sa.ForeignKey('lab_groups.id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )

    if not _has_table(bind, 'protocol_settings'):
        op.create_table('protocol_settings',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('terminal_gateway_url', sa.String(length=255), nullable=True),
            sa.Column('enable_web_terminal', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('enable_rdp', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('enable_spice', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('enable_novnc', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('default_ssh_port', sa.Integer(), nullable=False, server_default='22'),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        )

def downgrade() -> None:
    pass

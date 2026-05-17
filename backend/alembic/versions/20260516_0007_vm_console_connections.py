"""add vm console connections table

Revision ID: 20260516_0007
Revises: 20260516_0006
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260516_0007'
down_revision = '20260516_0006'
branch_labels = None
depends_on = None


def _has_table(bind, name):
    return inspect(bind).has_table(name)


def upgrade() -> None:
    b = op.get_bind()
    if not _has_table(b, 'vm_console_connections'):
        op.create_table(
            'vm_console_connections',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('vm_id', sa.Integer(), sa.ForeignKey('student_vms.id'), nullable=False, unique=True),
            sa.Column('proxmox_vmid', sa.Integer(), nullable=False),
            sa.Column('node', sa.String(length=100), nullable=True),
            sa.Column('protocol', sa.String(length=20), nullable=False),
            sa.Column('guacamole_connection_id', sa.String(length=100), nullable=False),
            sa.Column('guacamole_connection_name', sa.String(length=255), nullable=False),
            sa.Column('hostname', sa.String(length=255), nullable=False),
            sa.Column('port', sa.Integer(), nullable=False),
            sa.Column('username_mode', sa.String(length=50), nullable=True),
            sa.Column('credential_source', sa.String(length=50), nullable=True),
            sa.Column('last_verified_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    pass

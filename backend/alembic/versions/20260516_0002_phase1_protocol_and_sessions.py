"""phase1 protocol and session foundations

Revision ID: 20260516_0002
Revises: 20260515_0001
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260516_0002'
down_revision = '20260515_0001'
branch_labels = None
depends_on = None


def _has_col(table: str, col: str) -> bool:
    insp = inspect(op.get_bind())
    if table not in insp.get_table_names():
        return False
    return col in [c['name'] for c in insp.get_columns(table)]


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if 'student_vms' in insp.get_table_names():
        for name, col in [
            ('console_enabled', sa.Column('console_enabled', sa.Boolean(), nullable=True, server_default=sa.text('true'))),
            ('ssh_enabled', sa.Column('ssh_enabled', sa.Boolean(), nullable=True, server_default=sa.text('true'))),
            ('rdp_enabled', sa.Column('rdp_enabled', sa.Boolean(), nullable=True, server_default=sa.text('false'))),
            ('spice_enabled', sa.Column('spice_enabled', sa.Boolean(), nullable=True, server_default=sa.text('false'))),
            ('assigned_ip', sa.Column('assigned_ip', sa.String(length=64), nullable=True)),
            ('default_username', sa.Column('default_username', sa.String(length=100), nullable=True)),
            ('hostname', sa.Column('hostname', sa.String(length=255), nullable=True)),
            ('ssh_username', sa.Column('ssh_username', sa.String(length=100), nullable=True)),
            ('ssh_auth_method', sa.Column('ssh_auth_method', sa.String(length=50), nullable=True)),
            ('ssh_port', sa.Column('ssh_port', sa.Integer(), nullable=True, server_default='22')),
        ]:
            if not _has_col('student_vms', name):
                op.add_column('student_vms', col)

    insp = inspect(op.get_bind())
    if 'connection_launches' not in insp.get_table_names():
        op.create_table(
            'connection_launches',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('vm_id', sa.Integer(), sa.ForeignKey('student_vms.id'), nullable=False),
            sa.Column('protocol', sa.String(length=50), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
            sa.Column('details', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        )


def downgrade() -> None:
    pass

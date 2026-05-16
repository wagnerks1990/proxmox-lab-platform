"""phase1 protocol and session foundations

Revision ID: 20260516_0002
Revises: 20260515_0001
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa

revision = '20260516_0002'
down_revision = '20260515_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('student_vms', sa.Column('console_enabled', sa.Boolean(), nullable=True, server_default=sa.text('true')))
    op.add_column('student_vms', sa.Column('ssh_enabled', sa.Boolean(), nullable=True, server_default=sa.text('true')))
    op.add_column('student_vms', sa.Column('rdp_enabled', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    op.add_column('student_vms', sa.Column('spice_enabled', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    op.add_column('student_vms', sa.Column('assigned_ip', sa.String(length=64), nullable=True))
    op.add_column('student_vms', sa.Column('default_username', sa.String(length=100), nullable=True))
    op.add_column('student_vms', sa.Column('hostname', sa.String(length=255), nullable=True))
    op.add_column('student_vms', sa.Column('ssh_username', sa.String(length=100), nullable=True))
    op.add_column('student_vms', sa.Column('ssh_auth_method', sa.String(length=50), nullable=True))
    op.add_column('student_vms', sa.Column('ssh_port', sa.Integer(), nullable=True, server_default='22'))

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
    op.drop_table('connection_launches')
    op.drop_column('student_vms', 'ssh_port')
    op.drop_column('student_vms', 'ssh_auth_method')
    op.drop_column('student_vms', 'ssh_username')
    op.drop_column('student_vms', 'hostname')
    op.drop_column('student_vms', 'default_username')
    op.drop_column('student_vms', 'assigned_ip')
    op.drop_column('student_vms', 'spice_enabled')
    op.drop_column('student_vms', 'rdp_enabled')
    op.drop_column('student_vms', 'ssh_enabled')
    op.drop_column('student_vms', 'console_enabled')

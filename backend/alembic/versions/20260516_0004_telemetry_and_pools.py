"""add telemetry events and desktop pools

Revision ID: 20260516_0004
Revises: 20260516_0003
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa

revision = '20260516_0004'
down_revision = '20260516_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'telemetry_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='info'),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('vm_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    for col in ['event_type','severity','created_at','user_id','vm_id','session_id','request_id']:
        op.create_index(f'ix_telemetry_events_{col}', 'telemetry_events', [col])

    op.create_table(
        'desktop_pools',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False, unique=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('pool_type', sa.String(length=32), nullable=False),
        sa.Column('template_vmid', sa.Integer(), nullable=True),
        sa.Column('template_node', sa.String(length=50), nullable=True),
        sa.Column('default_protocol', sa.String(length=50), nullable=False),
        sa.Column('target_node', sa.String(length=50), nullable=True),
        sa.Column('storage', sa.String(length=100), nullable=True),
        sa.Column('bridge', sa.String(length=100), nullable=True),
        sa.Column('vlan_tag', sa.Integer(), nullable=True),
        sa.Column('vmid_start', sa.Integer(), nullable=True),
        sa.Column('vmid_end', sa.Integer(), nullable=True),
        sa.Column('naming_pattern', sa.String(length=100), nullable=True),
        sa.Column('desired_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('maintenance_mode', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    for col in ['name','pool_type','enabled','maintenance_mode']:
        op.create_index(f'ix_desktop_pools_{col}', 'desktop_pools', [col])


def downgrade() -> None:
    for col in ['name','pool_type','enabled','maintenance_mode']:
        op.drop_index(f'ix_desktop_pools_{col}', table_name='desktop_pools')
    op.drop_table('desktop_pools')
    for col in ['event_type','severity','created_at','user_id','vm_id','session_id','request_id']:
        op.drop_index(f'ix_telemetry_events_{col}', table_name='telemetry_events')
    op.drop_table('telemetry_events')

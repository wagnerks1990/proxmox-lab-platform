"""add vm_sessions table

Revision ID: 20260516_0003
Revises: 20260516_0002
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260516_0003'
down_revision = '20260516_0002'
branch_labels = None
depends_on = None


def _ensure_index(table: str, name: str, col: str) -> None:
    insp = inspect(op.get_bind())
    existing = {i['name'] for i in insp.get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, [col])


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if 'vm_sessions' not in insp.get_table_names():
        op.create_table(
        'vm_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('vm_id', sa.Integer(), sa.ForeignKey('student_vms.id'), nullable=False),
        sa.Column('pool_id', sa.Integer(), nullable=True),
        sa.Column('connection_launch_id', sa.Integer(), sa.ForeignKey('connection_launches.id'), nullable=True),
        sa.Column('protocol', sa.String(length=50), nullable=False),
        sa.Column('state', sa.String(length=32), nullable=False),
        sa.Column('node', sa.String(length=50), nullable=True),
        sa.Column('proxmox_vmid', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('launched_at', sa.DateTime(), nullable=True),
        sa.Column('disconnected_at', sa.DateTime(), nullable=True),
        sa.Column('expired_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('last_heartbeat_at', sa.DateTime(), nullable=True),
        sa.Column('failure_reason', sa.String(length=255), nullable=True),
        sa.Column('client_ip', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    for c in ['user_id','vm_id','state','protocol','created_at','request_id','connection_launch_id']:
        _ensure_index('vm_sessions', f'ix_vm_sessions_{c}', c)


def downgrade() -> None:
    for c in ['connection_launch_id','request_id','created_at','protocol','state','vm_id','user_id']:
        op.drop_index(f'ix_vm_sessions_{c}', table_name='vm_sessions')
    op.drop_table('vm_sessions')

"""deployment update control plane

Revision ID: 20260907_0010
Revises: 20260907_0009
Create Date: 2026-09-07
"""

from alembic import op
import sqlalchemy as sa


revision = '20260907_0010'
down_revision = '20260907_0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'deployment_update_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch', sa.String(length=120), nullable=False, server_default='main'),
        sa.Column('channel', sa.String(length=32), nullable=False, server_default='stable'),
        sa.Column('automatic_updates', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('check_interval_minutes', sa.Integer(), nullable=False, server_default='360'),
        sa.Column('maintenance_hour_utc', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("channel IN ('stable', 'candidate', 'development')", name='ck_deployment_update_channel'),
        sa.CheckConstraint('check_interval_minutes BETWEEN 15 AND 10080', name='ck_deployment_update_interval'),
        sa.CheckConstraint('maintenance_hour_utc BETWEEN 0 AND 23', name='ck_deployment_update_hour'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'deployment_update_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('requested_by', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('from_version', sa.String(length=64), nullable=True),
        sa.Column('to_version', sa.String(length=64), nullable=True),
        sa.Column('backup_path', sa.String(length=512), nullable=True),
        sa.Column('details', sa.String(length=2048), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_deployment_update_runs_requested_by', 'deployment_update_runs', ['requested_by'])
    op.create_index('ix_deployment_update_runs_status', 'deployment_update_runs', ['status'])
    op.execute(
        "INSERT INTO deployment_update_settings (branch, channel, automatic_updates, check_interval_minutes, maintenance_hour_utc) VALUES ('main', 'stable', false, 360, 7)"
    )


def downgrade() -> None:
    op.drop_index('ix_deployment_update_runs_status', table_name='deployment_update_runs')
    op.drop_index('ix_deployment_update_runs_requested_by', table_name='deployment_update_runs')
    op.drop_table('deployment_update_runs')
    op.drop_table('deployment_update_settings')

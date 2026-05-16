"""add worker runs

Revision ID: 20260516_0005
Revises: 20260516_0004
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa

revision = '20260516_0005'
down_revision = '20260516_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'worker_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('worker_name', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('started_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('summary_json', sa.Text(), nullable=True),
        sa.Column('error', sa.String(length=255), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
    )
    op.create_index('ix_worker_runs_worker_name', 'worker_runs', ['worker_name'])
    op.create_index('ix_worker_runs_status', 'worker_runs', ['status'])
    op.create_index('ix_worker_runs_started_at', 'worker_runs', ['started_at'])


def downgrade() -> None:
    op.drop_index('ix_worker_runs_started_at', table_name='worker_runs')
    op.drop_index('ix_worker_runs_status', table_name='worker_runs')
    op.drop_index('ix_worker_runs_worker_name', table_name='worker_runs')
    op.drop_table('worker_runs')

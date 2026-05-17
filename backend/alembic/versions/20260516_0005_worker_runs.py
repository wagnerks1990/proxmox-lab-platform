"""add worker runs

Revision ID: 20260516_0005
Revises: 20260516_0004
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260516_0005'
down_revision = '20260516_0004'
branch_labels = None
depends_on = None


def _ensure_index(table: str, name: str, col: str) -> None:
    insp = inspect(op.get_bind())
    existing = {i['name'] for i in insp.get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, [col])


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if 'worker_runs' not in insp.get_table_names():
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
    _ensure_index('worker_runs', 'ix_worker_runs_worker_name', 'worker_name')
    _ensure_index('worker_runs', 'ix_worker_runs_status', 'status')
    _ensure_index('worker_runs', 'ix_worker_runs_started_at', 'started_at')


def downgrade() -> None:
    op.drop_index('ix_worker_runs_started_at', table_name='worker_runs')
    op.drop_index('ix_worker_runs_status', table_name='worker_runs')
    op.drop_index('ix_worker_runs_worker_name', table_name='worker_runs')
    op.drop_table('worker_runs')

"""backfill desktop_pools.enabled for drifted deployments

Revision ID: 20260517_0010
Revises: 20260516_0009
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260517_0010'
down_revision = '20260516_0009'
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    insp = inspect(op.get_bind())
    if table not in insp.get_table_names():
        return False
    return column in {c['name'] for c in insp.get_columns(table)}


def _ensure_index(table: str, name: str, col: str) -> None:
    insp = inspect(op.get_bind())
    if table not in insp.get_table_names():
        return
    existing = {i['name'] for i in insp.get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, [col])


def upgrade() -> None:
    if _has_column('desktop_pools', 'enabled'):
        _ensure_index('desktop_pools', 'ix_desktop_pools_enabled', 'enabled')
        return

    bind = op.get_bind()
    insp = inspect(bind)
    if 'desktop_pools' not in insp.get_table_names():
        return

    op.add_column(
        'desktop_pools',
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.execute(sa.text('UPDATE desktop_pools SET enabled = true WHERE enabled IS NULL'))
    op.alter_column('desktop_pools', 'enabled', server_default=sa.true(), nullable=False)
    _ensure_index('desktop_pools', 'ix_desktop_pools_enabled', 'enabled')


def downgrade() -> None:
    pass

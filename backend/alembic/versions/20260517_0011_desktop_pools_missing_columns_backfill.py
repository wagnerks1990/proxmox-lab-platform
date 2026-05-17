"""backfill missing desktop_pools columns for older deployments

Revision ID: 20260517_0011
Revises: 20260517_0010
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260517_0011'
down_revision = '20260517_0010'
branch_labels = None
depends_on = None


def _table_exists(table: str) -> bool:
    return table in inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _table_exists(table):
        return False
    cols = inspect(op.get_bind()).get_columns(table)
    return column in {c['name'] for c in cols}


def _ensure_index(table: str, name: str, col: str) -> None:
    if not _table_exists(table):
        return
    existing = {i['name'] for i in inspect(op.get_bind()).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, [col])


def _add_col_if_missing(table: str, col: sa.Column) -> None:
    if not _has_column(table, col.name):
        op.add_column(table, col)


def upgrade() -> None:
    table = 'desktop_pools'
    if not _table_exists(table):
        return

    _add_col_if_missing(table, sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    _add_col_if_missing(table, sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    _add_col_if_missing(table, sa.Column('maintenance_mode', sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_col_if_missing(table, sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.execute(sa.text('UPDATE desktop_pools SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL'))
    op.execute(sa.text('UPDATE desktop_pools SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL'))
    op.execute(sa.text('UPDATE desktop_pools SET maintenance_mode = false WHERE maintenance_mode IS NULL'))
    op.execute(sa.text('UPDATE desktop_pools SET enabled = true WHERE enabled IS NULL'))

    op.alter_column(table, 'updated_at', nullable=False, server_default=sa.func.now())
    op.alter_column(table, 'created_at', nullable=False, server_default=sa.func.now())
    op.alter_column(table, 'maintenance_mode', nullable=False, server_default=sa.false())
    op.alter_column(table, 'enabled', nullable=False, server_default=sa.true())

    _ensure_index(table, 'ix_desktop_pools_enabled', 'enabled')
    _ensure_index(table, 'ix_desktop_pools_maintenance_mode', 'maintenance_mode')
    _ensure_index(table, 'ix_desktop_pools_name', 'name')
    _ensure_index(table, 'ix_desktop_pools_pool_type', 'pool_type')


def downgrade() -> None:
    pass

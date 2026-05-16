"""baseline migration marker

Revision ID: 20260515_0001
Revises:
Create Date: 2026-05-15
"""
from alembic import op

revision = '20260515_0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Baseline marker for migration-driven schema management.
    pass

def downgrade() -> None:
    pass

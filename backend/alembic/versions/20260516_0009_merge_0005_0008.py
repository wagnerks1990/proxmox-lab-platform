"""merge migration heads 0005 and 0008

Revision ID: 20260516_0009
Revises: 20260516_0005, 20260516_0008
Create Date: 2026-05-16
"""

revision = '20260516_0009'
down_revision = ('20260516_0005', '20260516_0008')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # merge-only revision: no schema change
    pass


def downgrade() -> None:
    pass

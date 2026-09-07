"""organization identity foundation

Revision ID: 20260907_0009
Revises: 20260907_0008
Create Date: 2026-09-07
"""

from alembic import op
import sqlalchemy as sa


revision = '20260907_0009'
down_revision = '20260907_0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('slug', sa.String(length=80), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)
    op.create_table(
        'organization_memberships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('student', 'instructor', 'admin', 'owner')", name='ck_organization_membership_role'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_organization_membership_user'),
    )
    op.create_index('ix_organization_memberships_organization_id', 'organization_memberships', ['organization_id'])
    op.create_index('ix_organization_memberships_user_id', 'organization_memberships', ['user_id'])

    # Preserve current alpha data in a visible compatibility tenant. A later
    # migration will require explicit resource assignment for production use.
    op.execute("INSERT INTO organizations (name, slug, enabled) VALUES ('Default Organization', 'default', true)")
    op.execute(
        """
        INSERT INTO organization_memberships (organization_id, user_id, role, is_active)
        SELECT o.id,
               u.id,
               CASE r.name
                   WHEN 'Admin' THEN 'owner'
                   WHEN 'Teacher' THEN 'instructor'
                   ELSE 'student'
               END,
               u.is_active
          FROM users u
          JOIN roles r ON r.id = u.role_id
          CROSS JOIN organizations o
         WHERE o.slug = 'default'
        """
    )


def downgrade() -> None:
    op.drop_index('ix_organization_memberships_user_id', table_name='organization_memberships')
    op.drop_index('ix_organization_memberships_organization_id', table_name='organization_memberships')
    op.drop_table('organization_memberships')
    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_table('organizations')

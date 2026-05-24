"""add user/group management tables

Revision ID: 20260524_0004
Revises: 20260522_0003
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa


revision = '20260524_0004'
down_revision = '20260522_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_table(
        'group_memberships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_in_group', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'user_id', name='uq_group_memberships_group_user'),
    )
    op.create_index('ix_group_memberships_group_id', 'group_memberships', ['group_id'])
    op.create_index('ix_group_memberships_user_id', 'group_memberships', ['user_id'])
    op.create_table(
        'group_template_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id']),
        sa.ForeignKeyConstraint(['template_id'], ['vm_templates.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'template_id', name='uq_group_template_permissions_group_template'),
    )
    op.create_index('ix_group_template_permissions_group_id', 'group_template_permissions', ['group_id'])
    op.create_index('ix_group_template_permissions_template_id', 'group_template_permissions', ['template_id'])


def downgrade() -> None:
    op.drop_index('ix_group_template_permissions_template_id', table_name='group_template_permissions')
    op.drop_index('ix_group_template_permissions_group_id', table_name='group_template_permissions')
    op.drop_table('group_template_permissions')
    op.drop_index('ix_group_memberships_user_id', table_name='group_memberships')
    op.drop_index('ix_group_memberships_group_id', table_name='group_memberships')
    op.drop_table('group_memberships')
    op.drop_table('groups')

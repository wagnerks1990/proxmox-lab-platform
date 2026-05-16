"""admin groups audit and user/desktop extensions

Revision ID: 20260516_0008
Revises: 20260516_0007
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260516_0008'
down_revision = '20260516_0007'
branch_labels = None
depends_on = None

def _has_table(bind, name):
    return inspect(bind).has_table(name)

def _has_column(bind, table, col):
    return any(c['name'] == col for c in inspect(bind).get_columns(table))

def _add(table, col):
    b = op.get_bind()
    if _has_table(b, table) and not _has_column(b, table, col.name):
        op.add_column(table, col)

def upgrade() -> None:
    b = op.get_bind()
    _add('users', sa.Column('display_name', sa.String(length=120), nullable=True))
    _add('users', sa.Column('force_password_change', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    _add('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))
    _add('users', sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()))

    if not _has_table(b, 'user_groups'):
        op.create_table('user_groups', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('name', sa.String(100), nullable=False, unique=True), sa.Column('description', sa.String(255), nullable=True), sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()), sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()))
    if not _has_table(b, 'user_group_members'):
        op.create_table('user_group_members', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('group_id', sa.Integer(), sa.ForeignKey('user_groups.id'), nullable=False), sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False), sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()))
    if not _has_table(b, 'audit_events'):
        op.create_table('audit_events', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('actor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False), sa.Column('action', sa.String(100), nullable=False), sa.Column('entity_type', sa.String(50), nullable=False), sa.Column('entity_id', sa.String(100), nullable=True), sa.Column('status', sa.String(20), nullable=False, server_default='success'), sa.Column('message', sa.String(255), nullable=True), sa.Column('details_json', sa.String(4000), nullable=True), sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()))

    _add('desktop_pools', sa.Column('assigned_group_id', sa.Integer(), sa.ForeignKey('user_groups.id'), nullable=True))
    _add('desktop_pools', sa.Column('placement_strategy', sa.String(length=50), nullable=True))
    _add('desktop_pools', sa.Column('allowed_protocols', sa.String(length=255), nullable=True))
    _add('desktop_pools', sa.Column('default_protocol', sa.String(length=20), nullable=True))
    _add('desktop_pools', sa.Column('idle_timeout_minutes', sa.Integer(), nullable=True))
    _add('desktop_pools', sa.Column('max_session_minutes', sa.Integer(), nullable=True))

def downgrade() -> None:
    pass

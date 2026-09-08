"""harden identity lifecycle and structured audit events

Revision ID: 20260908_0012
Revises: 20260907_0011
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa


revision = '20260908_0012'
down_revision = '20260907_0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(), nullable=True))

    op.create_table(
        'auth_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_id', sa.String(length=64), nullable=False),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('client_ip', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoke_reason', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_id'),
    )
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'])
    op.create_index('ix_auth_sessions_token_id', 'auth_sessions', ['token_id'], unique=True)
    op.create_index('ix_auth_sessions_expires_at', 'auth_sessions', ['expires_at'])
    op.create_index('ix_auth_sessions_revoked_at', 'auth_sessions', ['revoked_at'])

    op.create_table(
        'auth_login_attempts',
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('first_failure_at', sa.DateTime(), nullable=False),
        sa.Column('blocked_until', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('key_hash'),
    )
    op.create_index('ix_auth_login_attempts_blocked_until', 'auth_login_attempts', ['blocked_until'])

    op.alter_column('audit_logs', 'actor_id', existing_type=sa.Integer(), nullable=True)
    op.add_column('audit_logs', sa.Column('outcome', sa.String(length=32), nullable=False, server_default='success'))
    op.add_column('audit_logs', sa.Column('message', sa.String(length=512), nullable=True))
    op.add_column('audit_logs', sa.Column('request_id', sa.String(length=100), nullable=True))
    op.add_column('audit_logs', sa.Column('source_ip', sa.String(length=64), nullable=True))
    op.add_column('audit_logs', sa.Column('metadata_json', sa.String(), nullable=True))
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_request_id', table_name='audit_logs')
    op.drop_column('audit_logs', 'metadata_json')
    op.drop_column('audit_logs', 'source_ip')
    op.drop_column('audit_logs', 'request_id')
    op.drop_column('audit_logs', 'message')
    op.drop_column('audit_logs', 'outcome')
    op.alter_column('audit_logs', 'actor_id', existing_type=sa.Integer(), nullable=False)

    op.drop_index('ix_auth_login_attempts_blocked_until', table_name='auth_login_attempts')
    op.drop_table('auth_login_attempts')
    op.drop_index('ix_auth_sessions_revoked_at', table_name='auth_sessions')
    op.drop_index('ix_auth_sessions_expires_at', table_name='auth_sessions')
    op.drop_index('ix_auth_sessions_token_id', table_name='auth_sessions')
    op.drop_index('ix_auth_sessions_user_id', table_name='auth_sessions')
    op.drop_table('auth_sessions')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'token_version')

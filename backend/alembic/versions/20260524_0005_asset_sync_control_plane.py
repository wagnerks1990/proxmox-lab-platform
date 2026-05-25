"""asset sync control plane tables

Revision ID: 20260524_0005
Revises: 20260524_0004
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa


revision = '20260524_0005'
down_revision = '20260524_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'asset_catalog',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('asset_type', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=True),
        sa.Column('storage_id', sa.String(length=120), nullable=True),
        sa.Column('content_type', sa.String(length=32), nullable=True),
        sa.Column('source_node', sa.String(length=120), nullable=True),
        sa.Column('source_vmid', sa.Integer(), nullable=True),
        sa.Column('source_url', sa.String(length=1024), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('sha256', sa.String(length=128), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('sync_method', sa.String(length=64), nullable=False, server_default='download-url'),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_asset_catalog_asset_type', 'asset_catalog', ['asset_type'])

    op.create_table(
        'asset_node_state',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('asset_catalog.id'), nullable=False),
        sa.Column('node_name', sa.String(length=120), nullable=False),
        sa.Column('state', sa.String(length=32), nullable=False, server_default='missing'),
        sa.Column('target_vmid', sa.Integer(), nullable=True),
        sa.Column('target_volid', sa.String(length=255), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('sha256', sa.String(length=128), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.String(length=1024), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_asset_node_state_asset_id', 'asset_node_state', ['asset_id'])
    op.create_index('ix_asset_node_state_node_name', 'asset_node_state', ['node_name'])
    op.create_unique_constraint('uq_asset_node_state_asset_node', 'asset_node_state', ['asset_id', 'node_name'])

    op.create_table(
        'asset_sync_jobs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('asset_catalog.id'), nullable=True),
        sa.Column('target_node', sa.String(length=120), nullable=False),
        sa.Column('state', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('method', sa.String(length=64), nullable=False),
        sa.Column('source_node', sa.String(length=120), nullable=True),
        sa.Column('source_vmid', sa.Integer(), nullable=True),
        sa.Column('target_vmid', sa.Integer(), nullable=True),
        sa.Column('proxmox_upid', sa.String(length=255), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('error', sa.String(length=2048), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    op.create_table(
        'asset_sync_job_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('asset_sync_jobs.id'), nullable=False),
        sa.Column('level', sa.String(length=16), nullable=False, server_default='info'),
        sa.Column('message', sa.String(length=2048), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('asset_sync_job_events')
    op.drop_table('asset_sync_jobs')
    op.drop_constraint('uq_asset_node_state_asset_node', 'asset_node_state', type_='unique')
    op.drop_index('ix_asset_node_state_node_name', table_name='asset_node_state')
    op.drop_index('ix_asset_node_state_asset_id', table_name='asset_node_state')
    op.drop_table('asset_node_state')
    op.drop_index('ix_asset_catalog_asset_type', table_name='asset_catalog')
    op.drop_table('asset_catalog')

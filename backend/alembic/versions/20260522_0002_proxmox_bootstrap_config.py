"""proxmox bootstrap configuration tables

Revision ID: 20260522_0002
Revises: 20260521_0001
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa


revision = '20260522_0002'
down_revision = '20260521_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'proxmox_clusters',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('api_url', sa.String(length=255), nullable=False),
        sa.Column('verify_ssl', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('auth_mode', sa.String(length=32), nullable=False, server_default='token'),
        sa.Column('root_username', sa.String(length=120), nullable=True),
        sa.Column('token_user', sa.String(length=120), nullable=True),
        sa.Column('token_id', sa.String(length=120), nullable=True),
        sa.Column('encrypted_token_secret', sa.Text(), nullable=True),
        sa.Column('token_created_by_app', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('last_validated_at', sa.DateTime(), nullable=True),
        sa.Column('last_validation_status', sa.String(length=32), nullable=True),
        sa.Column('last_validation_error', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('name', name='uq_proxmox_clusters_name'),
    )

    op.create_table(
        'proxmox_nodes',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('cluster_id', sa.Integer(), nullable=False),
        sa.Column('node_name', sa.String(length=120), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('cpu_total', sa.Integer(), nullable=True),
        sa.Column('cpu_used', sa.Integer(), nullable=True),
        sa.Column('memory_total', sa.Integer(), nullable=True),
        sa.Column('memory_used', sa.Integer(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('raw_summary_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['proxmox_clusters.id'], name='fk_proxmox_nodes_cluster_id_clusters'),
    )
    op.create_index('ix_proxmox_nodes_cluster_id', 'proxmox_nodes', ['cluster_id'])

    op.create_table(
        'proxmox_cluster_defaults',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('cluster_id', sa.Integer(), nullable=False),
        sa.Column('default_node', sa.String(length=120), nullable=True),
        sa.Column('default_storage', sa.String(length=120), nullable=True),
        sa.Column('default_bridge', sa.String(length=120), nullable=True),
        sa.Column('default_template_vmid', sa.Integer(), nullable=True),
        sa.Column('clone_mode', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['cluster_id'], ['proxmox_clusters.id'], name='fk_proxmox_cluster_defaults_cluster_id_clusters'),
        sa.UniqueConstraint('cluster_id', name='uq_proxmox_cluster_defaults_cluster_id'),
    )
    op.create_index('ix_proxmox_cluster_defaults_cluster_id', 'proxmox_cluster_defaults', ['cluster_id'])


def downgrade() -> None:
    op.drop_index('ix_proxmox_cluster_defaults_cluster_id', table_name='proxmox_cluster_defaults')
    op.drop_table('proxmox_cluster_defaults')
    op.drop_index('ix_proxmox_nodes_cluster_id', table_name='proxmox_nodes')
    op.drop_table('proxmox_nodes')
    op.drop_table('proxmox_clusters')

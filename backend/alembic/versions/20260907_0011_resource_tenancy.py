"""scope classroom resources to organizations

Revision ID: 20260907_0011
Revises: 20260907_0010
Create Date: 2026-09-07
"""

from alembic import op
import sqlalchemy as sa


revision = '20260907_0011'
down_revision = '20260907_0010'
branch_labels = None
depends_on = None


TENANT_TABLES = ('vm_templates', 'student_vms', 'vm_sessions', 'desktop_pools', 'groups', 'classes', 'labs')


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.add_column(table, sa.Column('organization_id', sa.Integer(), nullable=True))
        op.execute(f"UPDATE {table} SET organization_id = (SELECT id FROM organizations WHERE slug = 'default')")
        op.alter_column(table, 'organization_id', existing_type=sa.Integer(), nullable=False)
        op.create_foreign_key(f'fk_{table}_organization_id', table, 'organizations', ['organization_id'], ['id'])
        op.create_index(f'ix_{table}_organization_id', table, ['organization_id'])

    # System events remain nullable; tenant-facing audit queries exclude them.
    op.add_column('audit_logs', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.execute("UPDATE audit_logs SET organization_id = (SELECT id FROM organizations WHERE slug = 'default')")
    op.create_foreign_key('fk_audit_logs_organization_id', 'audit_logs', 'organizations', ['organization_id'], ['id'])
    op.create_index('ix_audit_logs_organization_id', 'audit_logs', ['organization_id'])

    op.drop_constraint('uq_vm_templates_name', 'vm_templates', type_='unique')
    op.create_unique_constraint('uq_vm_templates_organization_name', 'vm_templates', ['organization_id', 'name'])
    op.drop_index('ix_desktop_pools_name', table_name='desktop_pools')
    op.create_index('ix_desktop_pools_name', 'desktop_pools', ['name'])
    op.create_unique_constraint('uq_desktop_pools_organization_name', 'desktop_pools', ['organization_id', 'name'])
    op.drop_constraint('groups_name_key', 'groups', type_='unique')
    op.create_unique_constraint('uq_groups_organization_name', 'groups', ['organization_id', 'name'])
    op.drop_constraint('uq_classes_name', 'classes', type_='unique')
    op.create_unique_constraint('uq_classes_organization_name', 'classes', ['organization_id', 'name'])


def downgrade() -> None:
    op.drop_constraint('uq_classes_organization_name', 'classes', type_='unique')
    op.create_unique_constraint('uq_classes_name', 'classes', ['name'])
    op.drop_constraint('uq_groups_organization_name', 'groups', type_='unique')
    op.create_unique_constraint('groups_name_key', 'groups', ['name'])
    op.drop_constraint('uq_desktop_pools_organization_name', 'desktop_pools', type_='unique')
    op.drop_index('ix_desktop_pools_name', table_name='desktop_pools')
    op.create_index('ix_desktop_pools_name', 'desktop_pools', ['name'], unique=True)
    op.drop_constraint('uq_vm_templates_organization_name', 'vm_templates', type_='unique')
    op.create_unique_constraint('uq_vm_templates_name', 'vm_templates', ['name'])
    op.drop_index('ix_audit_logs_organization_id', table_name='audit_logs')
    op.drop_constraint('fk_audit_logs_organization_id', 'audit_logs', type_='foreignkey')
    op.drop_column('audit_logs', 'organization_id')
    for table in reversed(TENANT_TABLES):
        op.drop_index(f'ix_{table}_organization_id', table_name=table)
        op.drop_constraint(f'fk_{table}_organization_id', table, type_='foreignkey')
        op.drop_column(table, 'organization_id')

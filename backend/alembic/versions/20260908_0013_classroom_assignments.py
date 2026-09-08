"""add classroom lab runs and explicit student assignments

Revision ID: 20260908_0013
Revises: 20260908_0012
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa


revision = '20260908_0013'
down_revision = '20260908_0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('enrollments', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        'lab_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('lab_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('state', sa.String(length=32), nullable=False, server_default='draft'),
        sa.Column('starts_at', sa.DateTime(), nullable=True),
        sa.Column('ends_at', sa.DateTime(), nullable=True),
        sa.Column('max_vms_per_student', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("state IN ('draft', 'scheduled', 'active', 'ended', 'cancelled')", name='ck_lab_runs_state'),
        sa.CheckConstraint('max_vms_per_student >= 1 AND max_vms_per_student <= 10', name='ck_lab_runs_vm_quota'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['lab_id'], ['labs.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_lab_runs_organization_id', 'lab_runs', ['organization_id'])
    op.create_index('ix_lab_runs_lab_id', 'lab_runs', ['lab_id'])
    op.create_index('ix_lab_runs_state', 'lab_runs', ['state'])
    op.create_index('ix_lab_runs_created_by', 'lab_runs', ['created_by'])

    op.create_table(
        'lab_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('lab_run_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('slot_index', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='assigned'),
        sa.Column('student_vm_id', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('assigned', 'ready', 'expired', 'revoked')", name='ck_lab_assignments_status'),
        sa.CheckConstraint('slot_index >= 1', name='ck_lab_assignments_slot'),
        sa.ForeignKeyConstraint(['lab_run_id'], ['lab_runs.id']),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['student_vm_id'], ['student_vms.id']),
        sa.ForeignKeyConstraint(['template_id'], ['vm_templates.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lab_run_id', 'user_id', 'slot_index', name='uq_lab_assignments_run_user_slot'),
        sa.UniqueConstraint('student_vm_id'),
    )
    op.create_index('ix_lab_assignments_organization_id', 'lab_assignments', ['organization_id'])
    op.create_index('ix_lab_assignments_lab_run_id', 'lab_assignments', ['lab_run_id'])
    op.create_index('ix_lab_assignments_user_id', 'lab_assignments', ['user_id'])
    op.create_index('ix_lab_assignments_template_id', 'lab_assignments', ['template_id'])
    op.create_index('ix_lab_assignments_status', 'lab_assignments', ['status'])
    op.create_index('ix_lab_assignments_student_vm_id', 'lab_assignments', ['student_vm_id'], unique=True)
    op.create_index('ix_lab_assignments_expires_at', 'lab_assignments', ['expires_at'])


def downgrade() -> None:
    op.drop_index('ix_lab_assignments_expires_at', table_name='lab_assignments')
    op.drop_index('ix_lab_assignments_student_vm_id', table_name='lab_assignments')
    op.drop_index('ix_lab_assignments_status', table_name='lab_assignments')
    op.drop_index('ix_lab_assignments_template_id', table_name='lab_assignments')
    op.drop_index('ix_lab_assignments_user_id', table_name='lab_assignments')
    op.drop_index('ix_lab_assignments_lab_run_id', table_name='lab_assignments')
    op.drop_index('ix_lab_assignments_organization_id', table_name='lab_assignments')
    op.drop_table('lab_assignments')
    op.drop_index('ix_lab_runs_created_by', table_name='lab_runs')
    op.drop_index('ix_lab_runs_state', table_name='lab_runs')
    op.drop_index('ix_lab_runs_lab_id', table_name='lab_runs')
    op.drop_index('ix_lab_runs_organization_id', table_name='lab_runs')
    op.drop_table('lab_runs')
    op.drop_column('enrollments', 'is_active')

"""sandbox_execution_jobs table for Phase 8

Revision ID: 20261021_0007
Revises: 20261021_0006
Create Date: 2026-10-21 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261021_0007'
down_revision: Union[str, None] = '20261021_0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sandbox_execution_jobs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workload_type', sa.String(length=50), nullable=False),
        sa.Column('command', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='queued', nullable=False),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('stdout', sa.Text(), nullable=True),
        sa.Column('stderr', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('memory_limit_mb', sa.Integer(), server_default='512', nullable=False),
        sa.Column('cpu_limit', sa.String(length=20), server_default='1.0', nullable=False),
        sa.Column('timeout_seconds', sa.Float(), server_default='30.0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sandbox_execution_jobs_id'), 'sandbox_execution_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_sandbox_execution_jobs_project_id'), 'sandbox_execution_jobs', ['project_id'], unique=False)
    op.create_index(op.f('ix_sandbox_execution_jobs_workload_type'), 'sandbox_execution_jobs', ['workload_type'], unique=False)
    op.create_index(op.f('ix_sandbox_execution_jobs_status'), 'sandbox_execution_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_sandbox_execution_jobs_created_at'), 'sandbox_execution_jobs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sandbox_execution_jobs_created_at'), table_name='sandbox_execution_jobs')
    op.drop_index(op.f('ix_sandbox_execution_jobs_status'), table_name='sandbox_execution_jobs')
    op.drop_index(op.f('ix_sandbox_execution_jobs_workload_type'), table_name='sandbox_execution_jobs')
    op.drop_index(op.f('ix_sandbox_execution_jobs_project_id'), table_name='sandbox_execution_jobs')
    op.drop_index(op.f('ix_sandbox_execution_jobs_id'), table_name='sandbox_execution_jobs')
    op.drop_table('sandbox_execution_jobs')

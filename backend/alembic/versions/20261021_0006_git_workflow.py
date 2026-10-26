"""git_audit_logs table for Phase 7

Revision ID: 20261021_0006
Revises: 20261021_0005
Create Date: 2026-10-21 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261021_0006'
down_revision: Union[str, None] = '20261021_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'git_audit_logs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('repository_id', sa.Uuid(), sa.ForeignKey('imported_repositories.id', ondelete='CASCADE'), nullable=True),
        sa.Column('operation', sa.String(length=50), nullable=False),
        sa.Column('branch', sa.String(length=100), nullable=True),
        sa.Column('commit_sha', sa.String(length=100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='success', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_git_audit_logs_id'), 'git_audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_git_audit_logs_project_id'), 'git_audit_logs', ['project_id'], unique=False)
    op.create_index(op.f('ix_git_audit_logs_repository_id'), 'git_audit_logs', ['repository_id'], unique=False)
    op.create_index(op.f('ix_git_audit_logs_operation'), 'git_audit_logs', ['operation'], unique=False)
    op.create_index(op.f('ix_git_audit_logs_status'), 'git_audit_logs', ['status'], unique=False)
    op.create_index(op.f('ix_git_audit_logs_created_at'), 'git_audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_git_audit_logs_created_at'), table_name='git_audit_logs')
    op.drop_index(op.f('ix_git_audit_logs_status'), table_name='git_audit_logs')
    op.drop_index(op.f('ix_git_audit_logs_operation'), table_name='git_audit_logs')
    op.drop_index(op.f('ix_git_audit_logs_repository_id'), table_name='git_audit_logs')
    op.drop_index(op.f('ix_git_audit_logs_project_id'), table_name='git_audit_logs')
    op.drop_index(op.f('ix_git_audit_logs_id'), table_name='git_audit_logs')
    op.drop_table('git_audit_logs')

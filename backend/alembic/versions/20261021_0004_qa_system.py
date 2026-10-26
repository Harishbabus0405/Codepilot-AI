"""qa_system tables

Revision ID: 20261021_0004
Revises: 20261021_0003
Create Date: 2026-10-21 11:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261021_0004'
down_revision: Union[str, None] = '20261021_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. qa_review_runs table
    op.create_table(
        'qa_review_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('generated_project_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('current_stage', sa.String(length=50), server_default='initialized', nullable=False),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('test_plan', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('repair_attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['generated_project_id'], ['generated_projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_qa_review_runs_id'), 'qa_review_runs', ['id'], unique=False)
    op.create_index(op.f('ix_qa_review_runs_project_id'), 'qa_review_runs', ['project_id'], unique=False)

    # 2. qa_findings table
    op.create_table(
        'qa_findings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('qa_run_id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('finding_type', sa.String(length=50), server_default='code_review', nullable=False),
        sa.Column('severity', sa.String(length=20), server_default='medium', nullable=False),
        sa.Column('category', sa.String(length=100), server_default='code_quality', nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('suggested_remediation', sa.Text(), nullable=False),
        sa.Column('proposed_code', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='open', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['qa_run_id'], ['qa_review_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_qa_findings_id'), 'qa_findings', ['id'], unique=False)
    op.create_index(op.f('ix_qa_findings_qa_run_id'), 'qa_findings', ['qa_run_id'], unique=False)
    op.create_index(op.f('ix_qa_findings_project_id'), 'qa_findings', ['project_id'], unique=False)
    op.create_index(op.f('ix_qa_findings_severity'), 'qa_findings', ['severity'], unique=False)
    op.create_index(op.f('ix_qa_findings_status'), 'qa_findings', ['status'], unique=False)
    op.create_index(op.f('ix_qa_findings_file_path'), 'qa_findings', ['file_path'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_qa_findings_file_path'), table_name='qa_findings')
    op.drop_index(op.f('ix_qa_findings_status'), table_name='qa_findings')
    op.drop_index(op.f('ix_qa_findings_severity'), table_name='qa_findings')
    op.drop_index(op.f('ix_qa_findings_project_id'), table_name='qa_findings')
    op.drop_index(op.f('ix_qa_findings_qa_run_id'), table_name='qa_findings')
    op.drop_index(op.f('ix_qa_findings_id'), table_name='qa_findings')
    op.drop_table('qa_findings')

    op.drop_index(op.f('ix_qa_review_runs_project_id'), table_name='qa_review_runs')
    op.drop_index(op.f('ix_qa_review_runs_id'), table_name='qa_review_runs')
    op.drop_table('qa_review_runs')

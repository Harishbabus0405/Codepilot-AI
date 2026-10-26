"""codegen tables

Revision ID: 20261021_0003
Revises: 20261021_0002
Create Date: 2026-10-21 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261021_0003'
down_revision: Union[str, None] = '20261021_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. generated_projects table
    op.create_table(
        'generated_projects',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('workflow_run_id', sa.Uuid(), nullable=True),
        sa.Column('template_type', sa.String(length=50), server_default='fullstack', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('manifest', sa.JSON(), nullable=True),
        sa.Column('total_files', sa.Integer(), server_default='0', nullable=False),
        sa.Column('generated_files_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workflow_run_id'], ['workflow_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generated_projects_id'), 'generated_projects', ['id'], unique=False)
    op.create_index(op.f('ix_generated_projects_project_id'), 'generated_projects', ['project_id'], unique=False)
    op.create_index(op.f('ix_generated_projects_workflow_run_id'), 'generated_projects', ['workflow_run_id'], unique=False)

    # 2. generated_files table
    op.create_table(
        'generated_files',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('generated_project_id', sa.Uuid(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('language', sa.String(length=50), server_default='plaintext', nullable=False),
        sa.Column('purpose', sa.String(length=255), server_default='', nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('checksum', sa.String(length=64), server_default='', nullable=False),
        sa.Column('is_modified_by_user', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['generated_project_id'], ['generated_projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generated_files_id'), 'generated_files', ['id'], unique=False)
    op.create_index(op.f('ix_generated_files_generated_project_id'), 'generated_files', ['generated_project_id'], unique=False)
    op.create_index(op.f('ix_generated_files_file_path'), 'generated_files', ['file_path'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_generated_files_file_path'), table_name='generated_files')
    op.drop_index(op.f('ix_generated_files_generated_project_id'), table_name='generated_files')
    op.drop_index(op.f('ix_generated_files_id'), table_name='generated_files')
    op.drop_table('generated_files')

    op.drop_index(op.f('ix_generated_projects_workflow_run_id'), table_name='generated_projects')
    op.drop_index(op.f('ix_generated_projects_project_id'), table_name='generated_projects')
    op.drop_index(op.f('ix_generated_projects_id'), table_name='generated_projects')
    op.drop_table('generated_projects')

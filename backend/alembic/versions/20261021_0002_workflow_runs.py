"""workflow runs table

Revision ID: 20261021_0002
Revises: 20261021_0001
Create Date: 2026-10-21 11:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261021_0002'
down_revision: Union[str, None] = '20261021_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workflow_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=False),
        sa.Column('correlation_id', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('current_stage', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('completed_stages', sa.JSON(), nullable=False),
        sa.Column('plan_output', sa.JSON(), nullable=True),
        sa.Column('architecture_output', sa.JSON(), nullable=True),
        sa.Column('validation_output', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_runs_id'), 'workflow_runs', ['id'], unique=False)
    op.create_index(op.f('ix_workflow_runs_project_id'), 'workflow_runs', ['project_id'], unique=False)
    op.create_index(op.f('ix_workflow_runs_correlation_id'), 'workflow_runs', ['correlation_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_workflow_runs_correlation_id'), table_name='workflow_runs')
    op.drop_index(op.f('ix_workflow_runs_project_id'), table_name='workflow_runs')
    op.drop_index(op.f('ix_workflow_runs_id'), table_name='workflow_runs')
    op.drop_table('workflow_runs')

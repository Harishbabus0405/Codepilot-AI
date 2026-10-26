"""Add repository_id and selected_branch to projects and workflow_runs

Revision ID: 20261022_0009
Revises: 20261022_0008
Create Date: 2026-10-22 19:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261022_0009'
down_revision: Union[str, None] = '20261022_0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add repository association columns to projects table
    with op.batch_alter_table('projects') as batch_op:
        batch_op.add_column(sa.Column('repository_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('selected_branch', sa.String(length=100), nullable=True))
        batch_op.create_foreign_key(
            'fk_projects_repository_id',
            'imported_repositories',
            ['repository_id'],
            ['id'],
            ondelete='SET NULL',
        )

    # 2. Add repository association columns to workflow_runs table
    with op.batch_alter_table('workflow_runs') as batch_op:
        batch_op.add_column(sa.Column('repo_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('selected_branch', sa.String(length=100), nullable=True))
        batch_op.create_foreign_key(
            'fk_workflow_runs_repo_id',
            'imported_repositories',
            ['repo_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('workflow_runs') as batch_op:
        batch_op.drop_constraint('fk_workflow_runs_repo_id', type_='foreignkey')
        batch_op.drop_column('selected_branch')
        batch_op.drop_column('repo_id')

    with op.batch_alter_table('projects') as batch_op:
        batch_op.drop_constraint('fk_projects_repository_id', type_='foreignkey')
        batch_op.drop_column('selected_branch')
        batch_op.drop_column('repository_id')

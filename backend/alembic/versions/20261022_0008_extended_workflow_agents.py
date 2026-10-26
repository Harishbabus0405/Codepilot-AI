"""Extended workflow agents and stage outputs

Revision ID: 20261022_0008
Revises: 20261021_0007
Create Date: 2026-10-22 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261022_0008'
down_revision: Union[str, None] = '20261021_0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new agent stage output columns to workflow_runs table
    with op.batch_alter_table('workflow_runs') as batch_op:
        batch_op.add_column(sa.Column('repo_understanding_output', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('developer_output', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('qa_output', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('security_output', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('code_review_output', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('documentation_output', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('pipeline_type', sa.String(length=50), server_default='full', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('workflow_runs') as batch_op:
        batch_op.drop_column('pipeline_type')
        batch_op.drop_column('documentation_output')
        batch_op.drop_column('code_review_output')
        batch_op.drop_column('security_output')
        batch_op.drop_column('qa_output')
        batch_op.drop_column('developer_output')
        batch_op.drop_column('repo_understanding_output')

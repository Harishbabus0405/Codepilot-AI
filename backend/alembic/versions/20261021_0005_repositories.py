"""imported_repositories table

Revision ID: 20261021_0005
Revises: 20261021_0004
Create Date: 2026-10-21 13:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261021_0005'
down_revision: Union[str, None] = '20261021_0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'imported_repositories',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('repo_url', sa.String(length=500), nullable=False),
        sa.Column('owner', sa.String(length=255), server_default='', nullable=False),
        sa.Column('default_branch', sa.String(length=100), server_default='main', nullable=False),
        sa.Column('is_private', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('total_files', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_chunks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_size_bytes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('index_path', sa.String(length=500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('last_indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_imported_repositories_id'), 'imported_repositories', ['id'], unique=False)
    op.create_index(op.f('ix_imported_repositories_name'), 'imported_repositories', ['name'], unique=False)
    op.create_index(op.f('ix_imported_repositories_repo_url'), 'imported_repositories', ['repo_url'], unique=False)
    op.create_index(op.f('ix_imported_repositories_status'), 'imported_repositories', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_imported_repositories_status'), table_name='imported_repositories')
    op.drop_index(op.f('ix_imported_repositories_repo_url'), table_name='imported_repositories')
    op.drop_index(op.f('ix_imported_repositories_name'), table_name='imported_repositories')
    op.drop_index(op.f('ix_imported_repositories_id'), table_name='imported_repositories')
    op.drop_table('imported_repositories')

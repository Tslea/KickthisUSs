"""Add GitHub integration fields

Revision ID: github_integration_001
Revises: previous_revision
Create Date: 2024-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'github_integration_001'
down_revision = None  # Sostituire con l'ultima revision
branch_labels = None
depends_on = None


def upgrade():
    # Aggiungi campi a Project
    op.add_column('project', sa.Column('github_repo_url', sa.String(length=500), nullable=True))
    op.add_column('project', sa.Column('github_sync_enabled', sa.Boolean(), nullable=True, server_default='1'))
    op.add_column('project', sa.Column('github_created_at', sa.DateTime(), nullable=True))
    
    # Aggiungi campi a Solution
    op.add_column('solution', sa.Column('github_branch_name', sa.String(length=200), nullable=True))
    op.add_column('solution', sa.Column('github_pr_url', sa.String(length=500), nullable=True))
    op.add_column('solution', sa.Column('github_commit_sha', sa.String(length=40), nullable=True))
    op.add_column('solution', sa.Column('github_pr_number', sa.Integer(), nullable=True))
    op.add_column('solution', sa.Column('github_synced_at', sa.DateTime(), nullable=True))
    
    # Aggiungi campi a User
    op.add_column('user', sa.Column('github_username', sa.String(length=100), nullable=True))
    op.create_unique_constraint('uq_user_github_username', 'user', ['github_username'])
    
    # Aggiungi campi a Comment
    op.add_column('comment', sa.Column('github_comment_id', sa.BigInteger(), nullable=True))
    op.create_unique_constraint('uq_comment_github_id', 'comment', ['github_comment_id'])


def downgrade():
    # Rimuovi constraint
    op.drop_constraint('uq_comment_github_id', 'comment', type_='unique')
    op.drop_constraint('uq_user_github_username', 'user', type_='unique')
    
    # Rimuovi colonne (ordine inverso)
    op.drop_column('comment', 'github_comment_id')
    op.drop_column('user', 'github_username')
    op.drop_column('solution', 'github_synced_at')
    op.drop_column('solution', 'github_pr_number')
    op.drop_column('solution', 'github_commit_sha')
    op.drop_column('solution', 'github_pr_url')
    op.drop_column('solution', 'github_branch_name')
    op.drop_column('project', 'github_created_at')
    op.drop_column('project', 'github_sync_enabled')
    op.drop_column('project', 'github_repo_url')

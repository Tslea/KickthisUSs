"""add_github_repo_name_to_project

Revision ID: 4cd333c1bb31
Revises: 2e4c6a7d5fb0
Create Date: 2025-10-22 15:26:31.940188

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4cd333c1bb31'
down_revision = '2e4c6a7d5fb0'
branch_labels = None
depends_on = None


def upgrade():
    # Aggiungi la colonna github_repo_name alla tabella project
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.add_column(sa.Column('github_repo_name', sa.String(length=100), nullable=True))


def downgrade():
    # Rimuovi la colonna github_repo_name
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_column('github_repo_name')

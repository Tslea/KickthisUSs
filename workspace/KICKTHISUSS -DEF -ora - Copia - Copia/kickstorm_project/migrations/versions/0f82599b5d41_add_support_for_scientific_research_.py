"""Add support for scientific research projects

Revision ID: 0f82599b5d41
Revises: 163d41bc6a4f
Create Date: 2025-09-05 23:27:43.438944

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0f82599b5d41'
down_revision = '163d41bc6a4f'
branch_labels = None
depends_on = None


def upgrade():
    # Aggiungi colonna project_type con default 'commercial'
    op.add_column('project', sa.Column('project_type', sa.String(20), nullable=False, server_default='commercial'))
    
    # Crea index per project_type
    op.create_index('ix_project_project_type', 'project', ['project_type'])
    
    # Per SQLite, non possiamo modificare direttamente le colonne esistenti
    # Ma possiamo lavorare con i constraint tramite batch operations
    with op.batch_alter_table('project') as batch_op:
        # SQLite permetterà di modificare la colonna in una batch operation
        batch_op.alter_column('creator_equity', nullable=True)


def downgrade():
    # Rimuovi le modifiche
    with op.batch_alter_table('project') as batch_op:
        batch_op.alter_column('creator_equity', nullable=False)
    
    op.drop_index('ix_project_project_type', 'project')
    op.drop_column('project', 'project_type')

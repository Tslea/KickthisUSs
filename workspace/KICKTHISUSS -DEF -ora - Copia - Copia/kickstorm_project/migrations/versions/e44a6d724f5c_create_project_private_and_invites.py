"""create_project_private_and_invites

Revision ID: e44a6d724f5c
Revises: fdfb86f1dab0
Create Date: 2025-07-14 21:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e44a6d724f5c'
down_revision = 'fdfb86f1dab0'
branch_labels = None
depends_on = None


def upgrade():
    # Aggiungi la colonna 'private' alla tabella 'project'
    op.add_column('project', sa.Column('private', sa.Boolean(), nullable=False, server_default='false'))

    # Crea la tabella 'project_invite'
    op.create_table('project_invite',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('inviter_id', sa.Integer(), nullable=False),
        sa.Column('invitee_id', sa.Integer(), nullable=False),
        sa.Column('invite_token', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['invitee_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['inviter_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invite_token')
    )
    
    # Crea gli indici per migliorare le performance
    op.create_index(op.f('ix_project_invite_invitee_id'), 'project_invite', ['invitee_id'], unique=False)
    op.create_index(op.f('ix_project_invite_inviter_id'), 'project_invite', ['inviter_id'], unique=False)
    op.create_index(op.f('ix_project_invite_project_id'), 'project_invite', ['project_id'], unique=False)


def downgrade():
    # Cancella gli indici
    op.drop_index(op.f('ix_project_invite_project_id'), table_name='project_invite')
    op.drop_index(op.f('ix_project_invite_inviter_id'), table_name='project_invite')
    op.drop_index(op.f('ix_project_invite_invitee_id'), table_name='project_invite')
    
    # Cancella la tabella 'project_invite'
    op.drop_table('project_invite')
    
    # Cancella la colonna 'private' dalla tabella 'project'
    op.drop_column('project', 'private')

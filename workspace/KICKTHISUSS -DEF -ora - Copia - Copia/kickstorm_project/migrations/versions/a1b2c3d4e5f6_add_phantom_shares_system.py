"""Add phantom shares system

Revision ID: a1b2c3d4e5f6
Revises: 2e4c6a7d5fb0
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '3e85c6276b1b'
branch_labels = None
depends_on = None


def upgrade():
    # Add total_shares column to project table
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_shares', sa.Numeric(20, 6), nullable=True))
    
    # Create phantom_share table
    op.create_table('phantom_share',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('shares_count', sa.Numeric(20, 6), nullable=False, server_default='0.0'),
        sa.Column('earned_from', sa.String(length=500), nullable=True, server_default=''),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'user_id', name='_project_user_share_uc')
    )
    with op.batch_alter_table('phantom_share', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_phantom_share_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_phantom_share_user_id'), ['user_id'], unique=False)
    
    # Create share_history table
    op.create_table('share_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('shares_change', sa.Numeric(20, 6), nullable=False),
        sa.Column('shares_before', sa.Numeric(20, 6), nullable=False),
        sa.Column('shares_after', sa.Numeric(20, 6), nullable=False),
        sa.Column('percentage_before', sa.Float(), nullable=False),
        sa.Column('percentage_after', sa.Float(), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('changed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('share_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_share_history_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_share_history_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_share_history_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_share_history_user_id'), ['user_id'], unique=False)


def downgrade():
    # Drop share_history table
    with op.batch_alter_table('share_history', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_share_history_user_id'))
        batch_op.drop_index(batch_op.f('ix_share_history_project_id'))
        batch_op.drop_index(batch_op.f('ix_share_history_created_at'))
        batch_op.drop_index(batch_op.f('ix_share_history_action'))
    op.drop_table('share_history')
    
    # Drop phantom_share table
    with op.batch_alter_table('phantom_share', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_phantom_share_user_id'))
        batch_op.drop_index(batch_op.f('ix_phantom_share_project_id'))
    op.drop_table('phantom_share')
    
    # Remove total_shares column from project table
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_column('total_shares')


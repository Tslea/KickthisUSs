"""Add revenue tracking and transparency system

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-27 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Create project_revenue table
    op.create_table('project_revenue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
        sa.Column('recorded_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['recorded_by_user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('project_revenue', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_project_revenue_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_project_revenue_recorded_at'), ['recorded_at'], unique=False)
    
    # Create revenue_distribution table
    op.create_table('revenue_distribution',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('shares_count', sa.Numeric(20, 6), nullable=False),
        sa.Column('percentage', sa.Float(), nullable=False),
        sa.Column('amount', sa.Numeric(20, 2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='EUR'),
        sa.Column('revenue_id', sa.Integer(), nullable=True),
        sa.Column('transaction_hash', sa.String(length=255), nullable=True),
        sa.Column('blockchain_network', sa.String(length=50), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('distributed_at', sa.DateTime(), nullable=True),
        sa.Column('distributed_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['distributed_by_user_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.ForeignKeyConstraint(['revenue_id'], ['project_revenue.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('revenue_distribution', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_revenue_distribution_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_revenue_distribution_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_revenue_distribution_distributed_at'), ['distributed_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_revenue_distribution_transaction_hash'), ['transaction_hash'], unique=False)
    
    # Create transparency_report table
    op.create_table('transparency_report',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('report_month', sa.Integer(), nullable=False),
        sa.Column('report_year', sa.Integer(), nullable=False),
        sa.Column('report_data', sa.Text(), nullable=False),
        sa.Column('total_revenue', sa.Numeric(20, 2), nullable=True, server_default='0'),
        sa.Column('total_distributions', sa.Numeric(20, 2), nullable=True, server_default='0'),
        sa.Column('new_holders_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('generated_by_system', sa.Boolean(), nullable=True, server_default='1'),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'report_month', 'report_year', name='_project_month_year_report_uc')
    )
    with op.batch_alter_table('transparency_report', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_transparency_report_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_transparency_report_report_year'), ['report_year'], unique=False)
        batch_op.create_index(batch_op.f('ix_transparency_report_generated_at'), ['generated_at'], unique=False)


def downgrade():
    # Drop transparency_report table
    with op.batch_alter_table('transparency_report', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_transparency_report_generated_at'))
        batch_op.drop_index(batch_op.f('ix_transparency_report_report_year'))
        batch_op.drop_index(batch_op.f('ix_transparency_report_project_id'))
    op.drop_table('transparency_report')
    
    # Drop revenue_distribution table
    with op.batch_alter_table('revenue_distribution', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_revenue_distribution_transaction_hash'))
        batch_op.drop_index(batch_op.f('ix_revenue_distribution_distributed_at'))
        batch_op.drop_index(batch_op.f('ix_revenue_distribution_user_id'))
        batch_op.drop_index(batch_op.f('ix_revenue_distribution_project_id'))
    op.drop_table('revenue_distribution')
    
    # Drop project_revenue table
    with op.batch_alter_table('project_revenue', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_project_revenue_recorded_at'))
        batch_op.drop_index(batch_op.f('ix_project_revenue_project_id'))
    op.drop_table('project_revenue')


"""Add performance indexes for common query patterns

Revision ID: performance_indexes_001
Revises: fdfb86f1dab0
Create Date: 2025-12-04 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'performance_indexes_001'
down_revision = 'fdfb86f1dab0'
branch_labels = None
depends_on = None


def upgrade():
    # Add indexes to Task model for better query performance
    with op.batch_alter_table('task', schema=None) as batch_op:
        # Add single column indexes
        batch_op.create_index('ix_task_phase', ['phase'], unique=False)
        batch_op.create_index('ix_task_is_private', ['is_private'], unique=False)
        
        # Add composite indexes for common query patterns
        batch_op.create_index('ix_task_project_status', ['project_id', 'status'], unique=False)
        batch_op.create_index('ix_task_project_is_private', ['project_id', 'is_private'], unique=False)
        batch_op.create_index('ix_task_project_status_is_private', ['project_id', 'status', 'is_private'], unique=False)

    # Add composite indexes to Project model for better query performance
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.create_index('ix_project_private_created_at', ['private', 'created_at'], unique=False)
        batch_op.create_index('ix_project_category_private', ['category', 'private'], unique=False)
        batch_op.create_index('ix_project_type_private', ['project_type', 'private'], unique=False)


def downgrade():
    # Remove Project indexes
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_index('ix_project_type_private')
        batch_op.drop_index('ix_project_category_private')
        batch_op.drop_index('ix_project_private_created_at')

    # Remove Task indexes
    with op.batch_alter_table('task', schema=None) as batch_op:
        batch_op.drop_index('ix_task_project_status_is_private')
        batch_op.drop_index('ix_task_project_is_private')
        batch_op.drop_index('ix_task_project_status')
        batch_op.drop_index('ix_task_is_private')
        batch_op.drop_index('ix_task_phase')

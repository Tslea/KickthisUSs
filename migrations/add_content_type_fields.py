"""
Migration: Add content_type fields to Solution and SolutionFile tables

This migration adds support for multiple content types (software, hardware, design, documentation, media)
to the solution and solution_file tables.

Run with: python migrations/add_content_type_fields.py
"""

from app import create_app, db
from app.models import Solution, SolutionFile
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    """Add content_type fields to tables"""
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("Starting migration: add_content_type_fields")
            
            # Add content_type to Solution table
            logger.info("Adding content_type to solution table...")
            db.session.execute(text("""
                ALTER TABLE solution 
                ADD COLUMN content_type VARCHAR(20) DEFAULT 'software'
            """))
            db.session.commit()
            logger.info("✓ Added content_type to solution table")
            
            # Add content_type and content_category to SolutionFile table
            logger.info("Adding content_type to solution_file table...")
            db.session.execute(text("""
                ALTER TABLE solution_file 
                ADD COLUMN content_type VARCHAR(20) DEFAULT 'software'
            """))
            db.session.commit()
            logger.info("✓ Added content_type to solution_file table")
            
            logger.info("Adding content_category to solution_file table...")
            db.session.execute(text("""
                ALTER TABLE solution_file 
                ADD COLUMN content_category VARCHAR(50)
            """))
            db.session.commit()
            logger.info("✓ Added content_category to solution_file table")
            
            # Create indexes for better query performance
            logger.info("Creating indexes...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_solution_content_type 
                ON solution(content_type)
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_solution_file_content_type 
                ON solution_file(content_type)
            """))
            db.session.commit()
            logger.info("✓ Created indexes")
            
            # Update existing records based on file_type
            logger.info("Updating existing records...")
            update_existing_records()
            
            logger.info("✅ Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            db.session.rollback()
            raise


def update_existing_records():
    """Update existing solutions and files with appropriate content_type"""
    try:
        # Update solution_file records based on file_type
        logger.info("Categorizing existing solution files...")
        
        # Hardware files
        db.session.execute(text("""
            UPDATE solution_file 
            SET content_type = 'hardware'
            WHERE file_type IN ('prototype', 'visual') 
            AND (
                original_filename LIKE '%.stl' OR
                original_filename LIKE '%.step' OR
                original_filename LIKE '%.kicad_pcb' OR
                original_filename LIKE '%.gbr'
            )
        """))
        
        # Design files
        db.session.execute(text("""
            UPDATE solution_file 
            SET content_type = 'design'
            WHERE original_filename LIKE '%.psd' OR
                  original_filename LIKE '%.ai' OR
                  original_filename LIKE '%.fig' OR
                  original_filename LIKE '%.sketch' OR
                  original_filename LIKE '%.xd'
        """))
        
        # Documentation files
        db.session.execute(text("""
            UPDATE solution_file 
            SET content_type = 'documentation'
            WHERE file_type = 'documentation' OR
                  original_filename LIKE '%.pdf' OR
                  original_filename LIKE '%.docx' OR
                  original_filename LIKE '%.pptx'
        """))
        
        # Media files
        db.session.execute(text("""
            UPDATE solution_file 
            SET content_type = 'media'
            WHERE original_filename LIKE '%.mp4' OR
                  original_filename LIKE '%.mp3' OR
                  original_filename LIKE '%.mov' OR
                  original_filename LIKE '%.wav'
        """))
        
        # Software files (default, already set)
        db.session.execute(text("""
            UPDATE solution_file 
            SET content_type = 'software'
            WHERE content_type IS NULL AND file_type = 'source'
        """))
        
        db.session.commit()
        logger.info("✓ Updated existing solution_file records")
        
        # Update solution records based on their files
        logger.info("Updating solution content_type based on files...")
        db.session.execute(text("""
            UPDATE solution s
            SET content_type = (
                SELECT sf.content_type
                FROM solution_file sf
                WHERE sf.solution_id = s.id
                LIMIT 1
            )
            WHERE s.id IN (SELECT DISTINCT solution_id FROM solution_file)
        """))
        db.session.commit()
        logger.info("✓ Updated solution records")
        
    except Exception as e:
        logger.error(f"Failed to update existing records: {e}")
        db.session.rollback()
        raise


def downgrade():
    """Remove content_type fields"""
    app = create_app()
    
    with app.app_context():
        try:
            logger.info("Starting rollback: remove content_type fields")
            
            # Drop indexes
            db.session.execute(text("DROP INDEX IF EXISTS idx_solution_content_type"))
            db.session.execute(text("DROP INDEX IF EXISTS idx_solution_file_content_type"))
            
            # Remove columns from solution_file
            db.session.execute(text("ALTER TABLE solution_file DROP COLUMN content_category"))
            db.session.execute(text("ALTER TABLE solution_file DROP COLUMN content_type"))
            
            # Remove column from solution
            db.session.execute(text("ALTER TABLE solution DROP COLUMN content_type"))
            
            db.session.commit()
            logger.info("✅ Rollback completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()

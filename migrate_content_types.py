"""
Quick migration script using Flask-Migrate or direct SQL
Run this from the project root
"""

import sys
import os
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

try:
    # Try Flask app approach
    from app import create_app, db
    from app.models import Solution, SolutionFile
    
    print("📦 Creating Flask app...")
    app = create_app()
    
    with app.app_context():
        print("🔧 Starting migration...")
        
        # For SQLite, we need to use raw SQL
        from sqlalchemy import text
        
        try:
            # Add content_type to solution
            print("➡️ Adding content_type to solution table...")
            db.session.execute(text("""
                ALTER TABLE solution 
                ADD COLUMN content_type VARCHAR(20) DEFAULT 'software'
            """))
            db.session.commit()
            print("✅ Added content_type to solution table")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("⚠️ content_type already exists in solution table")
                db.session.rollback()
            else:
                raise
        
        try:
            # Add content_type to solution_file
            print("➡️ Adding content_type to solution_file table...")
            db.session.execute(text("""
                ALTER TABLE solution_file 
                ADD COLUMN content_type VARCHAR(20) DEFAULT 'software'
            """))
            db.session.commit()
            print("✅ Added content_type to solution_file table")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("⚠️ content_type already exists in solution_file table")
                db.session.rollback()
            else:
                raise
        
        try:
            # Add content_category to solution_file
            print("➡️ Adding content_category to solution_file table...")
            db.session.execute(text("""
                ALTER TABLE solution_file 
                ADD COLUMN content_category VARCHAR(50)
            """))
            db.session.commit()
            print("✅ Added content_category to solution_file table")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("⚠️ content_category already exists in solution_file table")
                db.session.rollback()
            else:
                raise
        
        # Update existing records
        print("➡️ Updating existing records...")
        try:
            # Set default content_type for existing solutions
            result = db.session.execute(text("""
                UPDATE solution 
                SET content_type = 'software' 
                WHERE content_type IS NULL
            """))
            db.session.commit()
            print(f"✅ Updated {result.rowcount} solution records")
            
            # Set default content_type for existing files
            result = db.session.execute(text("""
                UPDATE solution_file 
                SET content_type = 'software' 
                WHERE content_type IS NULL
            """))
            db.session.commit()
            print(f"✅ Updated {result.rowcount} solution_file records")
            
        except Exception as e:
            print(f"⚠️ Update warning: {e}")
            db.session.rollback()
        
        print("\n✅ Migration completed successfully!\n")
        
        # Verify
        print("🔍 Verifying migration...")
        result = db.session.execute(text("PRAGMA table_info(solution)"))
        solution_cols = [row[1] for row in result]
        
        result = db.session.execute(text("PRAGMA table_info(solution_file)"))
        solution_file_cols = [row[1] for row in result]
        
        print(f"✓ solution columns: {', '.join(solution_cols)}")
        print(f"✓ solution_file columns: {', '.join(solution_file_cols)}")
        
        if 'content_type' in solution_cols:
            print("✅ solution.content_type verified")
        if 'content_type' in solution_file_cols:
            print("✅ solution_file.content_type verified")
        if 'content_category' in solution_file_cols:
            print("✅ solution_file.content_category verified")
        
        print("\n🎉 All done!")

except ImportError as e:
    print(f"❌ Error importing app: {e}")
    print("\n💡 Alternative: Use Flask-Migrate")
    print("Run these commands:")
    print("  flask db migrate -m 'Add content_type fields'")
    print("  flask db upgrade")
    sys.exit(1)

except Exception as e:
    print(f"❌ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

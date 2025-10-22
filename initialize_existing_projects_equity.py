"""
Script to initialize equity for all existing projects that don't have ProjectEquity records
Run with: python initialize_existing_projects_equity.py
"""

from app import create_app, db
from app.models import Project, ProjectEquity, User
from app.services.equity_service import EquityService

app = create_app()

with app.app_context():
    print("=" * 80)
    print("🔧 INITIALIZING EQUITY FOR EXISTING PROJECTS")
    print("=" * 80)
    
    equity_service = EquityService()
    
    # Get all projects
    projects = Project.query.all()
    print(f"\n📊 Found {len(projects)} total projects")
    
    initialized_count = 0
    skipped_count = 0
    error_count = 0
    
    for project in projects:
        print(f"\n{'─' * 80}")
        print(f"📁 Project: {project.name} (ID: {project.id})")
        print(f"   Creator: {project.creator.username} (ID: {project.creator_id})")
        
        # Check if equity already initialized
        existing_equity = ProjectEquity.query.filter_by(
            project_id=project.id,
            user_id=project.creator_id
        ).first()
        
        if existing_equity:
            print(f"   ✅ Already initialized ({existing_equity.equity_percentage:.2f}%)")
            skipped_count += 1
            continue
        
        try:
            # Initialize creator equity
            print(f"   🚀 Initializing creator equity...")
            equity_service.initialize_creator_equity(project)
            db.session.commit()
            
            # Verify
            creator_equity = ProjectEquity.query.filter_by(
                project_id=project.id,
                user_id=project.creator_id
            ).first()
            
            if creator_equity:
                print(f"   ✅ SUCCESS! Creator now has {creator_equity.equity_percentage:.2f}% equity")
                initialized_count += 1
            else:
                print(f"   ❌ FAILED: No equity record created")
                error_count += 1
                
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            db.session.rollback()
            error_count += 1
    
    print(f"\n{'=' * 80}")
    print("📊 SUMMARY:")
    print(f"   ✅ Initialized: {initialized_count} projects")
    print(f"   ⏭️  Skipped (already initialized): {skipped_count} projects")
    print(f"   ❌ Errors: {error_count} projects")
    print(f"   📈 Total: {len(projects)} projects")
    print("=" * 80)
    
    if initialized_count > 0:
        print("\n✨ Equity initialization complete!")
        print("🔍 Now check:")
        print("   1. Cap Table views should show creator equity")
        print("   2. Equity History should show 'initial' grants")
        print("   3. Dashboard equity should display correctly")
    
    if error_count > 0:
        print("\n⚠️  Some projects had errors. Check logs above.")

"""
Debug script to check equity data in database
Run with: python debug_equity_data.py
"""

from app import create_app, db
from app.models import Project, ProjectEquity, EquityHistory, User

app = create_app()

with app.app_context():
    print("=" * 80)
    print("🔍 DEBUG EQUITY DATA")
    print("=" * 80)
    
    # Get all projects
    projects = Project.query.all()
    print(f"\n📊 Total Projects: {len(projects)}")
    
    for project in projects:
        print(f"\n{'─' * 80}")
        print(f"📁 Project: {project.name} (ID: {project.id})")
        print(f"   Creator: {project.creator.username} (ID: {project.creator_id})")
        print(f"   Type: {project.project_type}")
        print(f"   Creator Equity (legacy): {project.creator_equity}%")
        print(f"   Platform Fee: {project.platform_fee}%")
        
        # Check ProjectEquity records
        equity_records = ProjectEquity.query.filter_by(project_id=project.id).all()
        print(f"\n   💰 ProjectEquity Records: {len(equity_records)}")
        if equity_records:
            total_equity = sum(e.equity_percentage for e in equity_records)
            print(f"   Total Distributed via ProjectEquity: {total_equity:.2f}%")
            for i, equity in enumerate(equity_records, 1):
                print(f"   {i}. {equity.user.username}: {equity.equity_percentage:.2f}% (from: {equity.earned_from})")
        else:
            print("   ⚠️ NO ProjectEquity records found!")
            print("   🔧 This means equity_service.initialize_creator_equity() was NEVER called")
        
        # Check EquityHistory records
        history_records = EquityHistory.query.filter_by(project_id=project.id).order_by(EquityHistory.created_at.asc()).all()
        print(f"\n   📜 EquityHistory Records: {len(history_records)}")
        if history_records:
            for i, entry in enumerate(history_records, 1):
                print(f"   {i}. [{entry.action.upper()}] {entry.user.username}: {entry.equity_change:+.2f}% ({entry.equity_before:.2f}% → {entry.equity_after:.2f}%)")
                print(f"      Reason: {entry.reason}")
                print(f"      Source: {entry.source_type} (ID: {entry.source_id})")
                print(f"      Date: {entry.created_at}")
        else:
            print("   ⚠️ NO EquityHistory records found!")
            print("   🔧 This means equity_service._log_equity_change() was NEVER called")
        
        # Check legacy Collaborator equity_share
        from app.models import Collaborator
        collaborators = Collaborator.query.filter_by(project_id=project.id).all()
        print(f"\n   👥 Collaborators (legacy system): {len(collaborators)}")
        if collaborators:
            total_collab_equity = sum(c.equity_share or 0.0 for c in collaborators)
            print(f"   Total via Collaborator.equity_share: {total_collab_equity:.2f}%")
            for i, collab in enumerate(collaborators, 1):
                print(f"   {i}. {collab.user.username}: {collab.equity_share or 0.0:.2f}% (role: {collab.role})")
    
    print(f"\n{'=' * 80}")
    print("✅ DEBUG COMPLETE")
    print("=" * 80)
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("1. If ProjectEquity is empty → run equity initialization for existing projects")
    print("2. If EquityHistory is empty → equity logging was not enabled before")
    print("3. Check if initialize_creator_equity() is called in routes_projects.py after project creation")
    print("4. Check if distribute_task_completion_equity() is called in api_solutions.py after solution approval")

"""
Fix missing equity initialization for projects created before equity system was added.
This script checks all projects and initializes equity for those missing it.
"""
from app import create_app
from app.models import Project, ProjectEquity, EquityHistory
from app.services.equity_service import EquityService
from app.extensions import db
from app.utils.db_utils import (
    create_app_context,
    find_projects_without_equity,
    print_project_equity_summary,
    confirm_action
)

app = create_app()

with app.app_context():
    equity_service = EquityService()
    
    # Find projects without equity
    projects_without_equity = find_projects_without_equity()
    
    print(f"\n{'='*80}")
    print(f"CHECKING {Project.query.count()} PROJECTS FOR MISSING EQUITY INITIALIZATION")
    print(f"{'='*80}\n")
    
    if not projects_without_equity:
        print("✅ All projects have proper equity initialization!")
        print("No action needed.")
    else:
        # Print details for each project
        for project in projects_without_equity:
            print_project_equity_summary(project)
        
        print(f"\n{'='*80}")
        print(f"FOUND {len(projects_without_equity)} PROJECTS WITHOUT EQUITY INITIALIZATION")
        print(f"{'='*80}\n")
        
        if confirm_action(f"Do you want to initialize equity for these {len(projects_without_equity)} projects?"):
            print("\nInitializing equity...")
            for project in projects_without_equity:
                try:
                    # Initialize equity using the service
                    creator_equity = equity_service.initialize_creator_equity(project)
                    print(f"✅ Initialized {project.creator_equity}% equity for project {project.id} ({project.name})")
                except Exception as e:
                    print(f"❌ Error initializing project {project.id}: {str(e)}")
                    db.session.rollback()
            
            print("\n" + "="*80)
            print("EQUITY INITIALIZATION COMPLETE")
            print("="*80)
            
            # Verify
            print("\nVerifying initialization...")
            for project in projects_without_equity:
                pe = ProjectEquity.query.filter_by(project_id=project.id, user_id=project.creator_id).first()
                eh = EquityHistory.query.filter_by(project_id=project.id, user_id=project.creator_id).first()
                
                if pe and eh:
                    print(f"✅ Project {project.id}: ProjectEquity={pe.equity_percentage}%, EquityHistory logged")
                else:
                    print(f"❌ Project {project.id}: Still missing records!")
        else:
            print("\nInitialization cancelled.")

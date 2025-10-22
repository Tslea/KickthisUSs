"""Verify creator equity corrections"""
from app import create_app
from app.models import db, Project, ProjectEquity

app = create_app()
with app.app_context():
    print("\n" + "="*80)
    print("VERIFICATION: ProjectEquity vs Project.creator_equity")
    print("="*80)
    
    equities = ProjectEquity.query.filter_by(earned_from='creator').all()
    all_match = True
    
    for equity in equities:
        project = Project.query.get(equity.project_id)
        match = abs(equity.equity_percentage - project.creator_equity) < 0.01
        status = "OK" if match else "MISMATCH"
        
        print(f"\nProject {equity.project_id}:")
        print(f"  ProjectEquity: {equity.equity_percentage}%")
        print(f"  Project.creator_equity: {project.creator_equity}%")
        print(f"  Status: {status}")
        
        if not match:
            all_match = False
    
    print("\n" + "="*80)
    if all_match:
        print("SUCCESS! All equity values match correctly!")
    else:
        print("ERROR: Some values don't match!")
    print("="*80)

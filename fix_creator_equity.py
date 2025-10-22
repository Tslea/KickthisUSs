"""Fix incorrect creator equity for all projects - use project.creator_equity"""
from app import create_app
from app.models import db, Project, ProjectEquity, EquityHistory

app = create_app()
with app.app_context():
    print("\n" + "="*80)
    print("🔧 FIXING CREATOR EQUITY TO MATCH PROJECT.creator_equity")
    print("="*80)
    
    # Get all projects
    projects = Project.query.all()
    fixed_count = 0
    
    for project in projects:
        creator_equity_record = ProjectEquity.query.filter_by(
            project_id=project.id,
            earned_from='creator'
        ).first()
        
        if creator_equity_record:
            current_equity = creator_equity_record.equity_percentage
            correct_equity = project.creator_equity  # Value set by creator at project creation
            
            print(f"\n📁 Project {project.id}: {project.name}")
            print(f"   Current ProjectEquity: {current_equity}%")
            print(f"   Project.creator_equity: {correct_equity}%")
            
            if abs(current_equity - correct_equity) > 0.01:  # Allow for floating point errors
                # Update equity record
                creator_equity_record.equity_percentage = correct_equity
                
                # Log the correction in equity history
                correction_entry = EquityHistory(
                    project_id=project.id,
                    user_id=creator_equity_record.user_id,
                    action='correction',
                    equity_change=correct_equity - current_equity,
                    equity_before=current_equity,
                    equity_after=correct_equity,
                    reason=f'Corrected creator allocation from {current_equity}% to {correct_equity}% (matching project.creator_equity set at creation)',
                    source_type='correction',
                    source_id=None,
                    changed_by_user_id=creator_equity_record.user_id
                )
                db.session.add(correction_entry)
                
                print(f"   ✅ FIXED: {current_equity}% → {correct_equity}%")
                fixed_count += 1
            else:
                print(f"   ✅ Already correct")
        else:
            print(f"\n📁 Project {project.id}: {project.name}")
            print(f"   ⚠️  No creator equity record found!")
    
    db.session.commit()
    
    print("\n" + "="*80)
    print(f"✨ CORRECTION COMPLETE! Fixed {fixed_count} projects")
    print("="*80)

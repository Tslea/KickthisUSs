"""Test direct equity_config access to reproduce InstrumentedList error"""
from app import create_app
from app.models import db, Project
from app.services.equity_service import EquityService

app = create_app()
with app.app_context():
    print("\n" + "="*80)
    print("TESTING equity_config ACCESS")
    print("="*80)
    
    # Test projects with EquityConfiguration
    for project_id in [4, 5]:
        project = Project.query.get(project_id)
        print(f"\n📁 Project {project_id}: {project.name}")
        print(f"   equity_config type: {type(project.equity_config)}")
        print(f"   equity_config value: {project.equity_config}")
        
        # Test direct access (this might fail)
        try:
            team_pct = project.equity_config.team_percentage
            print(f"   ❌ DIRECT ACCESS WORKED: team_percentage = {team_pct}%")
        except AttributeError as e:
            print(f"   ✅ DIRECT ACCESS FAILED (expected): {e}")
        
        # Test get_available_equity()
        try:
            available = project.get_available_equity()
            print(f"   get_available_equity(): {available}%")
        except Exception as e:
            print(f"   ❌ get_available_equity() FAILED: {e}")
        
        # Test validate_and_fix_equity()
        try:
            equity_service = EquityService()
            result = equity_service.validate_and_fix_equity(project)
            print(f"   validate_and_fix_equity(): {result}")
        except Exception as e:
            print(f"   ❌ validate_and_fix_equity() FAILED: {e}")
    
    print("\n" + "="*80)

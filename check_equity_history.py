"""Check EquityHistory records"""
from app import create_app
from app.models import EquityHistory

app = create_app()
with app.app_context():
    print("\n" + "="*80)
    print("EQUITY HISTORY RECORDS")
    print("="*80)
    
    total = EquityHistory.query.count()
    print(f"\nTotal records: {total}")
    
    corrections = EquityHistory.query.filter_by(action='correction').count()
    print(f"Correction records: {corrections}")
    
    initials = EquityHistory.query.filter_by(action='initial').count()
    print(f"Initial records: {initials}")
    
    # Show all actions
    from sqlalchemy import func
    actions = EquityHistory.query.with_entities(
        EquityHistory.action, 
        func.count(EquityHistory.id)
    ).group_by(EquityHistory.action).all()
    
    print("\nBreakdown by action:")
    for action, count in actions:
        print(f"  {action}: {count}")
    
    # Show sample corrections
    print("\nSample correction records:")
    corrections = EquityHistory.query.filter_by(action='correction').limit(5).all()
    for c in corrections:
        print(f"  Project {c.project_id}: {c.equity_before}% → {c.equity_after}% ({c.reason[:50]}...)")

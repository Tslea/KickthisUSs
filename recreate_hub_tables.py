from app import create_app, db
from app.hub_agents.models import HubProject, HubDocument, AIConversation, ValidationIssue

app = create_app()

with app.app_context():
    print("Dropping Hub Agents tables...")
    # Drop specific tables to avoid wiping the whole DB
    HubDocument.__table__.drop(db.engine, checkfirst=True)
    AIConversation.__table__.drop(db.engine, checkfirst=True)
    ValidationIssue.__table__.drop(db.engine, checkfirst=True)
    HubProject.__table__.drop(db.engine, checkfirst=True)
    
    print("Re-creating Hub Agents tables...")
    db.create_all()
    print("Tables recreated successfully!")

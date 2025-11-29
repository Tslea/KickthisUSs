from app import create_app, db
from app.hub_agents.models import HubProject, HubDocument, AIConversation, ValidationIssue

app = create_app()

with app.app_context():
    print("Creating Hub Agents tables...")
    db.create_all()
    print("Tables created successfully!")

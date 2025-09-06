#!/usr/bin/env python3
from app import create_app
from app.models import Project, User, Collaborator

app = create_app()
with app.app_context():
    # Trova il progetto 1
    project = Project.query.get(1)
    if project:
        print(f"Progetto: {project.name}")
        print(f"Creatore ID: {project.creator_id}")
        creator = User.query.get(project.creator_id)
        if creator:
            print(f"Creatore: {creator.username}")
        
        # Trova collaboratori
        collaborators = Collaborator.query.filter_by(project_id=1).all()
        print(f"Collaboratori: {len(collaborators)}")
        for collab in collaborators:
            user = User.query.get(collab.user_id)
            print(f"- {user.username if user else 'Unknown'} (ID: {collab.user_id})")
    else:
        print("Progetto 1 non trovato")

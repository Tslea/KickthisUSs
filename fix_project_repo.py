#!/usr/bin/env python
"""Update project 22 GitHub repository name"""

from app import create_app, db
from app.models import Project

app = create_app()

with app.app_context():
    project = db.session.get(Project, 22)
    
    if not project:
        print("Project 22 not found!")
    else:
        print(f"Current github_repo_name: {project.github_repo_name}")
        
        # Update to the correct repository name
        new_repo_name = "Tslea/inmail-23"  # Change this if different
        project.github_repo_name = new_repo_name
        
        db.session.commit()
        
        print(f"Updated to: {project.github_repo_name}")
        print("Done! Now restart Flask and try uploading again.")

#!/usr/bin/env python
"""Quick script to check project 22 GitHub configuration"""

from app import create_app, db
from app.models import Project

app = create_app()

with app.app_context():
    project = db.session.get(Project, 22)
    
    if not project:
        print("Project 22 not found in database!")
    else:
        print(f"Project 22 found:")
        print(f"   Name: {project.name}")
        print(f"   github_repo_name: {project.github_repo_name}")
        print(f"   github_repo_url: {getattr(project, 'github_repo_url', 'N/A')}")
        print(f"   repository_url: {getattr(project, 'repository_url', 'N/A')}")
        
        if not project.github_repo_name:
            print("\nPROBLEM: github_repo_name is empty!")
            print("The async sync will NOT run without this field.")
            print("\nTo fix, you need to set github_repo_name.")
            print("What is the GitHub repository name? (e.g., 'Tslea/InMail-23')")
        else:
            print(f"\ngithub_repo_name is set to: {project.github_repo_name}")
            print("Sync should work!")

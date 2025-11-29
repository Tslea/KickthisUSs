from datetime import datetime
from app.extensions import db

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # NUOVI CAMPI: GitHub Integration (nullable per retrocompatibilità)
    github_repo_url = db.Column(db.String(500), nullable=True)
    github_sync_enabled = db.Column(db.Boolean, default=True)
    github_created_at = db.Column(db.DateTime, nullable=True)

class Solution(db.Model):
    __tablename__ = 'solutions'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # NUOVI CAMPI: GitHub Integration
    github_branch_name = db.Column(db.String(200), nullable=True)
    github_pr_url = db.Column(db.String(500), nullable=True)
    github_commit_sha = db.Column(db.String(40), nullable=True)
    github_pr_number = db.Column(db.Integer, nullable=True)
    github_synced_at = db.Column(db.DateTime, nullable=True)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # NUOVO CAMPO: GitHub username per sync commenti
    github_username = db.Column(db.String(100), nullable=True, unique=True)

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    solution_id = db.Column(db.Integer, db.ForeignKey('solutions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # NUOVO CAMPO: ID commento GitHub per sincronizzazione
    github_comment_id = db.Column(db.BigInteger, nullable=True, unique=True)
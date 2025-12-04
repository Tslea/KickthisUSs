"""
Common database initialization utilities.
This module contains shared utilities for database setup and initialization scripts.
"""
from typing import Optional
from flask import Flask


def create_app_context(app_factory=None):
    """
    Create and return an app context for database operations.
    
    Args:
        app_factory: Optional app factory function. If None, uses default.
        
    Returns:
        Tuple of (app, app_context)
        
    Usage:
        >>> app, ctx = create_app_context()
        >>> with ctx:
        ...     # Perform database operations here
        ...     pass
    """
    if app_factory is None:
        from app import create_app
        app_factory = create_app
    
    app = app_factory()
    ctx = app.app_context()
    ctx.push()
    return app, ctx


def get_project_equity_status(project):
    """
    Check equity initialization status for a project.
    
    Args:
        project: Project model instance
        
    Returns:
        Dict with equity status information:
        {
            'has_creator_equity': bool,
            'creator_equity_percentage': float or None,
            'project_creator_equity': float,
            'is_initialized': bool
        }
    """
    from app.models import ProjectEquity
    
    creator_equity = ProjectEquity.query.filter_by(
        project_id=project.id,
        user_id=project.creator_id
    ).first()
    
    return {
        'has_creator_equity': creator_equity is not None,
        'creator_equity_percentage': creator_equity.equity_percentage if creator_equity else None,
        'project_creator_equity': project.creator_equity,
        'is_initialized': creator_equity is not None
    }


def find_projects_without_equity():
    """
    Find all projects that are missing equity initialization.
    
    Returns:
        List of projects without proper equity records
    """
    from app.models import Project, ProjectEquity
    
    all_projects = Project.query.all()
    projects_without_equity = []
    
    for project in all_projects:
        creator_equity = ProjectEquity.query.filter_by(
            project_id=project.id,
            user_id=project.creator_id
        ).first()
        
        if not creator_equity:
            projects_without_equity.append(project)
    
    return projects_without_equity


def print_project_equity_summary(project, status=None):
    """
    Print a formatted summary of a project's equity status.
    
    Args:
        project: Project model instance
        status: Optional pre-computed status dict (from get_project_equity_status)
    """
    if status is None:
        status = get_project_equity_status(project)
    
    print(f"\n📁 Project {project.id}: {project.name}")
    print(f"   Creator: User {project.creator_id}")
    print(f"   Project Creator Equity: {project.creator_equity}%")
    
    if status['has_creator_equity']:
        print(f"   Current Equity Record: {status['creator_equity_percentage']}%")
        if abs(status['creator_equity_percentage'] - status['project_creator_equity']) < 0.01:
            print(f"   ✅ Equity is correct")
        else:
            print(f"   ⚠️  Equity mismatch detected")
    else:
        print(f"   ❌ No ProjectEquity record found")


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    Ask user for confirmation before performing an action.
    
    Args:
        prompt: Question to ask the user
        default: Default response if user just presses Enter
        
    Returns:
        True if user confirms, False otherwise
    """
    valid_yes = ['yes', 'y']
    valid_no = ['no', 'n']
    
    default_str = " [Y/n]" if default else " [y/N]"
    response = input(prompt + default_str + ": ").lower().strip()
    
    if not response:
        return default
    
    if response in valid_yes:
        return True
    elif response in valid_no:
        return False
    else:
        print("Please answer 'yes' or 'no'")
        return confirm_action(prompt, default)

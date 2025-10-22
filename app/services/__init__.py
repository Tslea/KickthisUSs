# app/services/__init__.py
"""
Services package for KICKTHISUSS
Contains external integrations and business logic services.
"""

from .github_service import GitHubService
from .github_sync_service import GitHubSyncService

__all__ = ['GitHubService', 'GitHubSyncService']

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from flask import current_app

from app.extensions import db
from app.models import Project, ProjectRepository
from app.utils import db_transaction
from .github_sync_service import GitHubSyncService

logger = logging.getLogger(__name__)


class ManagedRepoService:
    """
    Gestisce i repository "managed" per i progetti KickthisUSs.
    - Se GitHub è disponibile, crea repo tramite GitHubSyncService.
    - In caso contrario, registra uno stato locale per future sincronizzazioni.
    """

    def __init__(self):
        self.github_sync = GitHubSyncService()

    def initialize_managed_repository(self, project: Project) -> Optional[ProjectRepository]:
        """
        Assicura che esista un record ProjectRepository per il progetto.
        Se GitHub è abilitato crea/recupera repo, altrimenti registra stato locale.
        """
        if not project or not project.id:
            logger.warning("Project must be persisted before initializing managed repository.")
            return None

        existing = ProjectRepository.query.filter_by(project_id=project.id).first()
        if existing:
            return existing

        provider = 'local'
        repo_name = project.github_repo_name
        branch = 'main'
        status = 'disabled'
        last_sync_at = None

        if self.github_sync.is_enabled():
            try:
                repo_info = self.github_sync.setup_project_repository(project)
            except Exception as exc:
                logger.error("Managed repo GitHub setup failed for project %s: %s", project.id, exc)
                repo_info = None

            if repo_info:
                provider = 'github_managed'
                repo_name = repo_info.get('full_name') or repo_info.get('name')
                branch = repo_info.get('default_branch', 'main')
                status = 'ready'
                last_sync_at = datetime.now(timezone.utc)
            else:
                status = 'pending'
        else:
            logger.info("GitHub sync disabled; recording local repository state for project %s", project.id)

        with db_transaction():
            repo_record = ProjectRepository(
                project_id=project.id,
                provider=provider,
                repo_name=repo_name,
                branch=branch,
                status=status,
                last_sync_at=last_sync_at
            )
            db.session.add(repo_record)
        return repo_record

    def update_repository_status(
        self,
        project: Project,
        status: str,
        *,
        last_sync_at: Optional[datetime] = None,
        branch: Optional[str] = None
    ) -> Optional[ProjectRepository]:
        """Aggiorna lo stato del repository gestito."""
        record = ProjectRepository.query.filter_by(project_id=project.id).first()
        if not record:
            return None

        record.status = status
        if last_sync_at:
            record.last_sync_at = last_sync_at
        if branch:
            record.branch = branch

        with db_transaction():
            db.session.add(record)

        return record


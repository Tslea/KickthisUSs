import pytest

from app.services.managed_repo_service import ManagedRepoService
from app.models import ProjectRepository
from tests.factories import ProjectFactory, UserFactory


def test_managed_repo_creates_record_without_github(app):
    """Verifica che venga creato il record locale se GitHub è disabilitato."""
    with app.app_context():
        user = UserFactory()
        project = ProjectFactory(creator=user)

        service = ManagedRepoService()
        # Forza il servizio GitHub in modalità disabilitata per il test
        service.github_sync.enabled = False

        repo_record = service.initialize_managed_repository(project)

        assert repo_record is not None
        assert repo_record.project_id == project.id
        assert repo_record.provider in ('local', 'github_managed')
        assert repo_record.branch == 'main'

        # Il record deve essere persistito nel database
        persisted = ProjectRepository.query.filter_by(project_id=project.id).first()
        assert persisted is not None


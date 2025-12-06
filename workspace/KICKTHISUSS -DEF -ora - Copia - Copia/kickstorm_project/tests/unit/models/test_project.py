# tests/unit/models/test_project.py
import pytest
from app.models import Project, ALLOWED_PROJECT_CATEGORIES
from tests.factories import UserFactory, ProjectFactory, TaskFactory
from app.extensions import db


class TestProjectModel:
    """Test per il modello Project."""

    def test_project_creation(self, app):
        """Test creazione progetto base."""
        with app.app_context():
            user = UserFactory()
            project = ProjectFactory(creator=user)
            
            assert project.name is not None
            assert project.creator_id == user.id
            assert project.created_at is not None
            assert project.category in ALLOWED_PROJECT_CATEGORIES

    def test_project_relationships(self, app):
        """Test relazioni progetto."""
        with app.app_context():
            user = UserFactory()
            project = ProjectFactory(creator=user)
            
            # Relazione con creator
            assert project.creator == user
            assert project in user.projects
            
            # Task del progetto
            task = TaskFactory(project=project, creator=user)
            assert task in project.tasks

    def test_project_string_representation(self, app):
        """Test rappresentazione stringa progetto."""
        with app.app_context():
            project = ProjectFactory(name='Test Project')
            assert str(project) == '<Project Test Project (commercial)>'

    def test_project_pitch_validation(self, app):
        """Test validazione pitch progetto."""
        with app.app_context():
            project = ProjectFactory()
            
            # Pitch normale
            assert len(project.pitch) <= 500
            
            # Pitch vuoto
            project_no_pitch = ProjectFactory(pitch='')
            assert project_no_pitch.pitch == ''

    def test_project_category_validation(self, app):
        """Test validazione categoria progetto."""
        with app.app_context():
            project = ProjectFactory()
            assert project.category in ALLOWED_PROJECT_CATEGORIES.keys()

    def test_project_optional_fields(self, app):
        """Test campi opzionali progetto."""
        with app.app_context():
            project = ProjectFactory(
                cover_image_url=None,
                repository_url=None,
                description=''
            )
            
            assert project.cover_image_url is None
            assert project.repository_url is None
            assert project.description == ''

    def test_project_tasks_cascade_delete(self, app):
        """Test cancellazione a cascata task."""
        with app.app_context():
            user = UserFactory()
            project = ProjectFactory(creator=user)
            task = TaskFactory(project=project, creator=user)
            
            task_id = task.id
            project_id = project.id
            
            # Elimina progetto
            db.session.delete(project)
            db.session.commit()
            
            # Verifica che il task sia stato eliminato
            from app.models import Task
            deleted_task = db.session.get(Task, task_id)
            assert deleted_task is None

    def test_project_collaboration_features(self, app):
        """Test funzionalità collaborative progetto."""
        with app.app_context():
            project = ProjectFactory()
            
            # Verifica relazioni per collaborazione
            assert hasattr(project, 'collaborators')
            assert hasattr(project, 'activities')
            assert hasattr(project, 'notifications')

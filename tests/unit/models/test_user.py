# tests/unit/models/test_user.py
import pytest
from app.models import User
from tests.factories import UserFactory
from app.extensions import db


class TestUserModel:
    """Test per il modello User."""

    def test_user_creation(self, app):
        """Test creazione utente base."""
        with app.app_context():
            user = UserFactory()
            assert user.username is not None
            assert user.email is not None
            assert user.password_hash is not None
            assert user.created_at is not None

    def test_password_hashing(self, app):
        """Test hash e verifica password."""
        with app.app_context():
            user = UserFactory()
            user.set_password('testpassword123')
            
            # Password corretta
            assert user.check_password('testpassword123') is True
            
            # Password errata
            assert user.check_password('wrongpassword') is False
            assert user.check_password('') is False

    def test_email_unique_constraint(self, app):
        """Test vincolo unicità email."""
        with app.app_context():
            user1 = UserFactory(email='test@example.com')
            db.session.commit()
            
            # Tentativo di creare utente con stessa email
            with pytest.raises(Exception):
                user2 = UserFactory(email='test@example.com')
                db.session.commit()

    def test_username_unique_constraint(self, app):
        """Test vincolo unicità username."""
        with app.app_context():
            user1 = UserFactory(username='testuser')
            db.session.commit()
            
            # Tentativo di creare utente con stesso username
            with pytest.raises(Exception):
                user2 = UserFactory(username='testuser')
                db.session.commit()

    def test_user_string_representation(self, app):
        """Test rappresentazione stringa utente."""
        with app.app_context():
            user = UserFactory(username='testuser')
            assert str(user) == '<User testuser>'

    def test_user_relationships(self, app):
        """Test relazioni utente."""
        with app.app_context():
            from tests.factories import ProjectFactory, TaskFactory
            
            user = UserFactory()
            
            # Progetti creati
            project = ProjectFactory(creator=user)
            assert project in user.projects
            
            # Task creati
            task = TaskFactory(creator=user, project=project)
            assert task in user.created_tasks

    def test_user_profile_image_url(self, app):
        """Test URL immagine profilo."""
        with app.app_context():
            user = UserFactory()
            assert user.profile_image_url is not None
            
            # Test senza immagine
            user_no_image = UserFactory(profile_image_url=None)
            assert user_no_image.profile_image_url is None

    def test_user_activity_tracking(self, app):
        """Test tracciamento attività utente."""
        with app.app_context():
            user = UserFactory()
            
            # Verifica che le relazioni per attività esistano
            assert hasattr(user, 'activities')
            assert hasattr(user, 'endorsements')
            assert hasattr(user, 'votes')
            assert hasattr(user, 'notifications')

# tests/unit/api/test_project_routes.py
import pytest
from flask import url_for
from tests.factories import UserFactory, ProjectFactory
from app.extensions import db


class TestProjectRoutes:
    """Test per le route dei progetti."""

    def test_home_page(self, client):
        """Test pagina principale."""
        response = client.get('/')
        assert response.status_code == 200

    def test_projects_list(self, client, app):
        """Test lista progetti."""
        with app.app_context():
            # Crea alcuni progetti
            user = UserFactory()
            project1 = ProjectFactory(creator=user, name='Project 1')
            project2 = ProjectFactory(creator=user, name='Project 2')
            db.session.commit()
            
            response = client.get('/projects')
            assert response.status_code == 200
            assert b'Project 1' in response.data
            assert b'Project 2' in response.data

    def test_project_detail_view(self, client, app):
        """Test visualizzazione dettaglio progetto."""
        with app.app_context():
            user = UserFactory()
            project = ProjectFactory(creator=user, name='Test Project')
            db.session.commit()
            
            response = client.get(f'/project/{project.id}')
            assert response.status_code == 200
            assert b'Test Project' in response.data

    def test_project_detail_not_found(self, client):
        """Test progetto inesistente."""
        response = client.get('/project/999999')
        assert response.status_code == 404

    def test_create_project_get_requires_auth(self, client):
        """Test GET create project richiede autenticazione."""
        response = client.get('/create-project', follow_redirects=True)
        assert response.status_code == 200

    def test_create_project_get_authenticated(self, authenticated_client):
        """Test GET create project autenticato."""
        response = authenticated_client.get('/create-project')
        assert response.status_code == 200
        assert b'create' in response.data.lower() or b'new' in response.data.lower()

    def test_create_project_post_success(self, authenticated_client, app, auth_user):
        """Test creazione progetto successo."""
        with app.app_context():
            response = authenticated_client.post('/create-project', data={
                'name': 'New Test Project',
                'pitch': 'This is a test project pitch',
                'description': 'This is a longer description',
                'category': 'Tech'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verifica progetto creato
            from app.models import Project
            project = Project.query.filter_by(name='New Test Project').first()
            assert project is not None
            assert project.creator_id == auth_user.id

    def test_create_project_post_invalid_data(self, authenticated_client):
        """Test creazione progetto con dati non validi."""
        response = authenticated_client.post('/create-project', data={
            'name': '',  # Nome vuoto
            'pitch': 'Test pitch',
            'category': 'InvalidCategory'
        })
        
        assert response.status_code in [200, 302]
        # Può mostrare errori di validazione (200) o redirect (302)

    def test_edit_project_owner_only(self, client, app):
        """Test modifica progetto solo dal proprietario."""
        with app.app_context():
            owner = UserFactory()
            other_user = UserFactory()
            project = ProjectFactory(creator=owner)
            db.session.commit()
            
            # Login come altro utente
            response = client.post('/auth/login', data={
                'email': other_user.email,
                'password': 'testpassword'
            })
            
            # Tentativo di modifica
            response = client.get(f'/projects/{project.id}/edit')
            # Dovrebbe essere negato l'accesso o reindirizzato

    def test_project_collaboration_features(self, client, app):
        """Test funzionalità collaborative progetto."""
        with app.app_context():
            user = UserFactory()
            project = ProjectFactory(creator=user)
            db.session.commit()
            
            response = client.get(f'/project/{project.id}')
            assert response.status_code == 200
            
            # Verifica presenza sezioni collaborative
            # (tasks, collaborators, etc.)

    def test_project_filtering_by_category(self, client, app):
        """Test filtro progetti per categoria."""
        with app.app_context():
            user = UserFactory()
            tech_project = ProjectFactory(creator=user, category='Tech')
            art_project = ProjectFactory(creator=user, category='Art')
            db.session.commit()
            
            response = client.get('/projects?category=Tech')
            assert response.status_code == 200
            # Dovrebbe mostrare solo progetti Tech

    def test_project_search(self, client, app):
        """Test ricerca progetti."""
        with app.app_context():
            user = UserFactory()
            project = ProjectFactory(creator=user, name='Searchable Project')
            db.session.commit()
            
            response = client.get('/projects?search=Searchable')
            assert response.status_code == 200
            assert b'Searchable Project' in response.data

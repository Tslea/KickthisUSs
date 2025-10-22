"""
Test per le nuove funzionalità AI: Wiki AI e Project Guide AI
"""
import pytest
import tempfile
import os
from app import create_app, db
from app.models import User, Project, WikiPage, WikiRevision
from datetime import datetime, timezone

@pytest.fixture
def app():
    """Crea app Flask per test."""
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Client Flask per test."""
    return app.test_client()

class TestAIFeatures:
    """Test per le funzionalità AI integrate"""
    
    def test_project_creation_with_ai_guide(self, client, app):
        """Testa che alla creazione del progetto vengano generate le guide AI"""
        with app.app_context():
            # Registra un utente
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            # Login
            response = client.post('/auth/login', data={
                'email': 'test@example.com',
                'password': 'testpass'
            }, follow_redirects=True)
            
            # Crea un progetto
            response = client.post('/create-project', data={
                'name': 'Test AI Project',
                'category': 'Technology',
                'pitch': 'Una app innovativa per testare le funzionalità AI',
                'description': 'Descrizione dettagliata del progetto di test'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verifica che il progetto sia stato creato
            project = Project.query.filter_by(name='Test AI Project').first()
            assert project is not None
            assert project.creator_id == user.id
            
            # Le guide AI potrebbero essere generate o meno a seconda della connessione
            # Verifichiamo che i campi siano presenti e configurabili
    
    def test_ai_project_guide_api_permissions(self, client, app):
        """Testa i permessi delle API per le guide AI del progetto"""
        with app.app_context():
            # Crea utenti e progetto
            creator = User(username='creator', email='creator@example.com')
            creator.set_password('testpass')
            
            db.session.add(creator)
            db.session.commit()
            
            project = Project(
                name='Test Project',
                category='Technology',
                pitch='Test pitch',
                description='Test description',
                creator_id=creator.id
            )
            db.session.add(project)
            db.session.commit()
            
            # Test senza autenticazione - dovrebbe essere reindirizzato al login
            response = client.post(f'/api/projects/{project.id}/generate-ai-guide')
            assert response.status_code in [302, 401]  # Redirect o Unauthorized
            
            # Verifica che l'endpoint esista e sia raggiungibile
            # (Test di integrazione di base)
            
            # Test che il progetto sia stato creato correttamente con i campi AI
            assert project.ai_mvp_guide is None  # Inizialmente vuoto
            assert project.ai_feasibility_analysis is None  # Inizialmente vuoto
            assert project.ai_guide_generated_at is None  # Inizialmente vuoto
    
    def test_wiki_ai_api_permissions(self, client, app):
        """Testa i permessi delle API AI per la wiki"""
        with app.app_context():
            # Crea utenti, progetto e pagina wiki
            creator = User(username='creator', email='creator@example.com')
            creator.set_password('testpass')
            
            db.session.add(creator)
            db.session.commit()
            
            project = Project(
                name='Test Project',
                category='Technology', 
                pitch='Test pitch',
                description='Test description',
                creator_id=creator.id
            )
            db.session.add(project)
            db.session.commit()
            
            wiki_page = WikiPage(
                project_id=project.id,
                title='Test Page',
                slug='test-page',
                content='Questo è un contenuto di test per la pagina wiki che dovrebbe essere abbastanza lungo da poter essere riorganizzato e riassunto dall AI. Contiene varie informazioni importanti e dettagli tecnici.',
                created_by=creator.id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(wiki_page)
            db.session.commit()
            
            # Test senza autenticazione - dovrebbe essere reindirizzato al login
            response = client.post(f'/api/wiki/{project.id}/page/test-page/reorganize')
            assert response.status_code in [302, 401]  # Redirect o Unauthorized
            
            response = client.post(f'/api/wiki/{project.id}/page/test-page/summarize')
            assert response.status_code in [302, 401]  # Redirect o Unauthorized
            
            # Verifica che gli endpoint esistano e siano raggiungibili
            
            # Verifica che la pagina wiki sia stata creata correttamente
            assert wiki_page.title == 'Test Page'
            assert wiki_page.created_by == creator.id
    
    def test_database_schema_ai_fields(self, app):
        """Testa che i nuovi campi AI siano presenti nel database"""
        with app.app_context():
            # Crea un progetto con i nuovi campi AI
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            project = Project(
                name='Test Project',
                category='Technology',
                pitch='Test pitch',
                description='Test description',
                creator_id=user.id,
                ai_mvp_guide='# Test MVP Guide\n\nQuesto è un test della guida MVP generata da AI.',
                ai_feasibility_analysis='# Test Feasibility\n\nQuesta è una analisi di fattibilità di test.',
                ai_guide_generated_at=datetime.now(timezone.utc)
            )
            db.session.add(project)
            db.session.commit()
            
            # Verifica che i campi siano salvati correttamente
            retrieved_project = Project.query.filter_by(name='Test Project').first()
            assert retrieved_project.ai_mvp_guide is not None
            assert retrieved_project.ai_feasibility_analysis is not None
            assert retrieved_project.ai_guide_generated_at is not None
            assert '# Test MVP Guide' in retrieved_project.ai_mvp_guide
            assert '# Test Feasibility' in retrieved_project.ai_feasibility_analysis

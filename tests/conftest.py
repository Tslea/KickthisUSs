# tests/conftest.py
import pytest
import tempfile
import os
from app import create_app
from app.extensions import db as _db
from app.models import User, Project, Task, Solution, Vote, Notification
from tests.factories import UserFactory, ProjectFactory, TaskFactory, SolutionFactory


@pytest.fixture
def app():
    """Crea app Flask per test con database temporaneo."""
    db_fd, db_path = tempfile.mkstemp()
    
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-for-testing-only',
        'MAIL_SUPPRESS_SEND': True,  # Disabilita invio email nei test
        'OPENAI_API_KEY': 'test-openai-key',
        'AI_SERVICE_ENABLED': False,  # Disabilita AI nei test
    }
    
    app = create_app(test_config)
    
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()
        
        # Chiudi tutte le connessioni al database
        _db.session.close()
        _db.engine.dispose()
    
    # Chiudi il file descriptor prima di eliminare il file
    try:
        os.close(db_fd)
    except OSError:
        pass  # Già chiuso
    
    try:
        os.unlink(db_path)
    except (OSError, PermissionError):
        pass  # File già eliminato o in uso


@pytest.fixture
def client(app):
    """Client Flask per test HTTP."""
    return app.test_client()


@pytest.fixture
def db(app):
    """Istanza database per test."""
    with app.app_context():
        yield _db


@pytest.fixture
def runner(app):
    """Runner CLI per test comandi."""
    return app.test_cli_runner()


@pytest.fixture
def auth_user(app):
    """Utente autenticato per test."""
    with app.app_context():
        user = UserFactory()
        # Memorizza l'ID prima che l'oggetto diventi detached
        user_id = user.id
        user._id = user_id  # Aggiungo un attributo per memorizzare l'ID
        return user


@pytest.fixture
def admin_user(app):
    """Utente admin per test privilegi."""
    with app.app_context():
        user = UserFactory(username='admin', email='admin@test.com')
        _db.session.add(user)
        _db.session.commit()
        return user


@pytest.fixture
def sample_project(app, auth_user):
    """Progetto di esempio per test."""
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        _db.session.add(project)
        _db.session.commit()
        return project


@pytest.fixture
def sample_task(app, sample_project):
    """Task di esempio per test."""
    with app.app_context():
        task = TaskFactory(project=sample_project, creator=sample_project.creator)
        _db.session.add(task)
        _db.session.commit()
        return task


@pytest.fixture
def authenticated_client(client, auth_user):
    """Client con utente già autenticato."""
    # Usa l'ID memorizzato per evitare DetachedInstanceError
    user_id = getattr(auth_user, '_id', auth_user.id)
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user_id)
        sess['_fresh'] = True
    return client


@pytest.fixture
def sample_users(app):
    """Lista di utenti per test multi-utente."""
    with app.app_context():
        users = []
        for i in range(5):
            user = UserFactory(
                username=f'user{i}',
                email=f'user{i}@test.com'
            )
            _db.session.add(user)
            users.append(user)
        _db.session.commit()
        return users


@pytest.fixture
def sample_solution(app, sample_task, auth_user):
    """Soluzione di esempio per test."""
    with app.app_context():
        solution = SolutionFactory(
            task=sample_task,
            submitter=auth_user
        )
        _db.session.add(solution)
        _db.session.commit()
        return solution


# Helper functions for tests
def login_user(client, user):
    """Helper per login utente nei test."""
    return client.post('/auth/login', data={
        'email': user.email,
        'password': 'testpassword'
    }, follow_redirects=True)


def logout_user(client):
    """Helper per logout utente nei test."""
    return client.get('/auth/logout', follow_redirects=True)

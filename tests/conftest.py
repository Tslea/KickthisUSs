# tests/conftest.py
"""
Enhanced pytest configuration with comprehensive fixtures.
Includes caching, AI mocking, and schema validation helpers.
"""
import pytest
import tempfile
import os
import shutil
from unittest.mock import MagicMock, patch
from app import create_app
from app.extensions import db as _db
from app.models import User, Project, Task, Solution, Vote, Notification
from tests.factories import UserFactory, ProjectFactory, TaskFactory, SolutionFactory


# ============================================
# Pytest Markers Configuration
# ============================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "ai: marks tests requiring AI service")
    config.addinivalue_line("markers", "cache: marks tests involving caching")


# ============================================
# Core Application Fixtures
# ============================================

@pytest.fixture
def app():
    """Crea app Flask per test con database temporaneo."""
    db_fd, db_path = tempfile.mkstemp()
    
    test_workspace = os.path.join(os.path.dirname(db_path), 'workspace')
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-for-testing-only',
        'MAIL_SUPPRESS_SEND': True,  # Disabilita invio email nei test
        'OPENAI_API_KEY': 'test-openai-key',
        'AI_SERVICE_ENABLED': False,  # Disabilita AI nei test
        'PROJECT_WORKSPACE_ROOT': test_workspace,
        'PROJECT_WORKSPACE_MAX_ZIP_MB': 500,
        'PROJECT_WORKSPACE_MAX_FILE_MB': 100,
        'PROJECT_WORKSPACE_MAX_FILES': 5000,
        'PROJECT_WORKSPACE_MAX_ZIP_BYTES': 500 * 1024 * 1024,
        'PROJECT_WORKSPACE_MAX_FILE_BYTES': 100 * 1024 * 1024,
        'MAX_CONTENT_LENGTH': 600 * 1024 * 1024,
        # Caching config for tests
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 60,
    }
    
    app = create_app(test_config)
    
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
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

    workspace_dir = test_config.get('PROJECT_WORKSPACE_ROOT')
    if workspace_dir:
        shutil.rmtree(workspace_dir, ignore_errors=True)


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
        user = UserFactory(verify_email=True)
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


# ============================================
# Caching Fixtures
# ============================================

@pytest.fixture
def cache(app):
    """Get cache instance for testing."""
    from app.cache import cache as app_cache
    with app.app_context():
        app_cache.clear()
        yield app_cache
        app_cache.clear()


@pytest.fixture
def cached_data(cache):
    """Pre-populate cache with test data."""
    test_data = {
        'project:1': {'id': 1, 'name': 'Test Project'},
        'user:1': {'id': 1, 'username': 'testuser'},
    }
    for key, value in test_data.items():
        cache.set(key, value)
    return test_data


# ============================================
# AI Service Fixtures
# ============================================

@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing without API calls."""
    mock = MagicMock()
    mock.available = True
    mock.generate_structured_output.return_value = {
        'name': 'Generated Project Name',
        'description': 'Generated description',
        'rewritten_pitch': 'Enhanced pitch content'
    }
    mock.chat_with_context.return_value = "AI response for testing"
    mock.generate_document.return_value = "# Generated Document\n\nTest content"
    mock.analyze_solution.return_value = {
        'coherence_score': 0.85,
        'coherence_motivation': 'Good alignment',
        'completeness_score': 0.90,
        'completeness_motivation': 'Comprehensive solution'
    }
    return mock


@pytest.fixture
def ai_enabled_app(app, mock_ai_service):
    """App with mocked AI service."""
    with patch('app.services.ai_enhanced_service.enhanced_ai_service', mock_ai_service):
        yield app


# ============================================
# Schema Validation Fixtures
# ============================================

@pytest.fixture
def valid_project_data():
    """Valid project creation data."""
    return {
        'pitch': 'This is a test project pitch with enough characters to pass validation.',
        'category': 'tech',
        'project_type': 'commercial'
    }


@pytest.fixture
def valid_task_data():
    """Valid task creation data."""
    return {
        'title': 'Implement feature X',
        'description': 'This task involves implementing feature X with detailed specifications and requirements.',
        'task_type': 'implementation',
        'phase': 'Development',
        'difficulty': 'Medium',
        'equity_reward': 25.0,
        'is_private': False
    }


@pytest.fixture
def valid_solution_data():
    """Valid solution submission data."""
    return {
        'content': 'This is a comprehensive solution that addresses all requirements of the task with detailed implementation.',
        'github_pr_url': None
    }


@pytest.fixture
def valid_comment_data():
    """Valid comment data."""
    return {
        'content': 'This is a helpful comment.'
    }


# ============================================
# RAG Service Fixtures
# ============================================

@pytest.fixture
def mock_rag_service():
    """Mock RAG service for testing."""
    mock = MagicMock()
    mock.is_ready = True
    mock.initialize.return_value = True
    mock.index_document.return_value = True
    mock.query.return_value = []
    mock.query_context.return_value = "Relevant context from documents"
    return mock


# ============================================
# Helper Functions
# ============================================

def login_user(client, user):
    """Helper per login utente nei test."""
    return client.post('/auth/login', data={
        'email': user.email,
        'password': 'testpassword'
    }, follow_redirects=True)


def logout_user(client):
    """Helper per logout utente nei test."""
    return client.get('/auth/logout', follow_redirects=True)


def assert_valid_json_response(response, status_code=200):
    """Assert response is valid JSON with expected status."""
    assert response.status_code == status_code
    assert response.content_type == 'application/json'
    return response.get_json()


def assert_validation_error(response, field=None):
    """Assert response contains validation error."""
    assert response.status_code == 400
    data = response.get_json()
    assert 'errors' in data or 'error' in data
    if field and 'errors' in data:
        assert any(field in str(err) for err in data['errors'])
    return data

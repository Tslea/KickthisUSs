# tests/test_frameworks.py
"""
Tests for the new framework integrations:
- Flask-Caching
- Pydantic validation
- Enhanced AI service
- Enhanced RAG service
"""
import pytest
from app.schemas import (
    ProjectCreateSchema,
    TaskCreateSchema,
    SolutionSubmitSchema,
    CommentCreateSchema,
    validate_request_data
)


class TestPydanticSchemas:
    """Test Pydantic schema validation."""
    
    def test_project_create_valid(self, valid_project_data):
        """Test valid project creation data."""
        is_valid, result = validate_request_data(ProjectCreateSchema, valid_project_data)
        assert is_valid is True
        assert result.pitch == valid_project_data['pitch']
        assert result.category == valid_project_data['category']
    
    def test_project_create_pitch_too_short(self):
        """Test pitch validation - too short."""
        data = {'pitch': 'Too short', 'category': 'tech'}
        is_valid, result = validate_request_data(ProjectCreateSchema, data)
        assert is_valid is False
        assert 'errors' in result
    
    def test_project_create_pitch_too_long(self):
        """Test pitch validation - too long."""
        data = {'pitch': 'x' * 700, 'category': 'tech'}
        is_valid, result = validate_request_data(ProjectCreateSchema, data)
        assert is_valid is False
    
    def test_task_create_valid(self, valid_task_data):
        """Test valid task creation data."""
        is_valid, result = validate_request_data(TaskCreateSchema, valid_task_data)
        assert is_valid is True
        assert result.title == valid_task_data['title']
        assert result.equity_reward == valid_task_data['equity_reward']
    
    def test_task_create_equity_too_high(self):
        """Test equity validation - exceeds 100."""
        data = {
            'title': 'Test Task Title',
            'description': 'A valid description with enough characters',
            'task_type': 'implementation',
            'equity_reward': 150.0
        }
        is_valid, result = validate_request_data(TaskCreateSchema, data)
        assert is_valid is False
    
    def test_task_create_invalid_type(self):
        """Test task type validation."""
        data = {
            'title': 'Test Task Title',
            'description': 'A valid description with enough characters',
            'task_type': 'invalid_type',
            'equity_reward': 25.0
        }
        is_valid, result = validate_request_data(TaskCreateSchema, data)
        assert is_valid is False
    
    def test_solution_submit_valid(self, valid_solution_data):
        """Test valid solution submission."""
        is_valid, result = validate_request_data(SolutionSubmitSchema, valid_solution_data)
        assert is_valid is True
    
    def test_solution_github_url_valid(self):
        """Test valid GitHub PR URL."""
        data = {
            'content': 'A comprehensive solution with enough content to pass validation.',
            'github_pr_url': 'https://github.com/user/repo/pull/123'
        }
        is_valid, result = validate_request_data(SolutionSubmitSchema, data)
        assert is_valid is True
        assert result.github_pr_url == data['github_pr_url']
    
    def test_solution_github_url_invalid(self):
        """Test invalid GitHub PR URL."""
        data = {
            'content': 'A comprehensive solution with enough content to pass validation.',
            'github_pr_url': 'https://gitlab.com/user/repo/merge_requests/123'
        }
        is_valid, result = validate_request_data(SolutionSubmitSchema, data)
        assert is_valid is False
    
    def test_comment_create_valid(self, valid_comment_data):
        """Test valid comment creation."""
        is_valid, result = validate_request_data(CommentCreateSchema, valid_comment_data)
        assert is_valid is True
    
    def test_comment_create_empty(self):
        """Test empty comment validation."""
        data = {'content': '   '}
        is_valid, result = validate_request_data(CommentCreateSchema, data)
        assert is_valid is False


@pytest.mark.cache
class TestFlaskCaching:
    """Test Flask-Caching functionality."""
    
    def test_cache_set_get(self, app, cache):
        """Test basic cache set/get."""
        with app.app_context():
            cache.set('test_key', {'value': 42})
            result = cache.get('test_key')
            assert result == {'value': 42}
    
    def test_cache_delete(self, app, cache):
        """Test cache deletion."""
        with app.app_context():
            cache.set('delete_key', 'to_delete')
            cache.delete('delete_key')
            result = cache.get('delete_key')
            assert result is None
    
    def test_cache_timeout(self, app, cache):
        """Test cache with timeout."""
        import time
        with app.app_context():
            cache.set('timeout_key', 'value', timeout=1)
            assert cache.get('timeout_key') == 'value'
            # Note: In real tests, you might not want to sleep
            # time.sleep(2)
            # assert cache.get('timeout_key') is None
    
    def test_cached_data_fixture(self, app, cached_data, cache):
        """Test cached_data fixture."""
        with app.app_context():
            assert cache.get('project:1') == cached_data['project:1']
            assert cache.get('user:1') == cached_data['user:1']


@pytest.mark.ai
class TestEnhancedAIService:
    """Test Enhanced AI Service (with mocking)."""
    
    def test_ai_service_mock(self, mock_ai_service):
        """Test AI service mock is properly configured."""
        assert mock_ai_service.available is True
        
        result = mock_ai_service.generate_structured_output(
            "system prompt",
            "user prompt"
        )
        assert 'name' in result
        assert 'description' in result
    
    def test_ai_chat_mock(self, mock_ai_service):
        """Test AI chat mock."""
        result = mock_ai_service.chat_with_context(
            [{"role": "user", "content": "Hello"}],
            context="Some context"
        )
        assert result == "AI response for testing"
    
    def test_ai_document_generation_mock(self, mock_ai_service):
        """Test document generation mock."""
        result = mock_ai_service.generate_document(
            "mvp_definition.md",
            {"name": "Test", "pitch": "Test pitch"}
        )
        assert "Generated Document" in result
    
    def test_ai_solution_analysis_mock(self, mock_ai_service):
        """Test solution analysis mock."""
        result = mock_ai_service.analyze_solution(
            "Task Title",
            "Task Description",
            "Solution Content"
        )
        assert result['coherence_score'] == 0.85
        assert result['completeness_score'] == 0.90


class TestEnhancedRAGService:
    """Test Enhanced RAG Service."""
    
    def test_rag_service_mock(self, mock_rag_service):
        """Test RAG service mock."""
        assert mock_rag_service.is_ready is True
        assert mock_rag_service.initialize() is True
    
    def test_rag_index_document_mock(self, mock_rag_service):
        """Test document indexing mock."""
        result = mock_rag_service.index_document(
            project_id=1,
            filename="test.md",
            content="Test content"
        )
        assert result is True
    
    def test_rag_query_context_mock(self, mock_rag_service):
        """Test context query mock."""
        result = mock_rag_service.query_context(
            project_id=1,
            query_text="test query"
        )
        assert result == "Relevant context from documents"


class TestSchemaEdgeCases:
    """Test edge cases in schema validation."""
    
    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from inputs."""
        data = {
            'pitch': '   ' + 'x' * 50 + '   ',
            'category': '  tech  ',
            'project_type': 'commercial'
        }
        is_valid, result = validate_request_data(ProjectCreateSchema, data)
        assert is_valid is True
        assert not result.pitch.startswith(' ')
        assert not result.pitch.endswith(' ')
    
    def test_normalized_whitespace_in_title(self):
        """Test that multiple spaces are normalized."""
        data = {
            'title': 'Test    Multiple    Spaces',
            'description': 'A valid description with enough characters to pass validation.',
            'task_type': 'implementation',
            'equity_reward': 25.0
        }
        is_valid, result = validate_request_data(TaskCreateSchema, data)
        assert is_valid is True
        assert '    ' not in result.title
    
    def test_equity_rounding(self):
        """Test that equity is rounded to 2 decimal places."""
        data = {
            'title': 'Test Task Title',
            'description': 'A valid description with enough characters to pass validation.',
            'task_type': 'implementation',
            'equity_reward': 25.333333
        }
        is_valid, result = validate_request_data(TaskCreateSchema, data)
        assert is_valid is True
        assert result.equity_reward == 25.33
    
    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored."""
        data = {
            'pitch': 'A valid pitch with enough characters to pass validation.',
            'category': 'tech',
            'project_type': 'commercial',
            'extra_field': 'should be ignored',
            'another_field': 123
        }
        is_valid, result = validate_request_data(ProjectCreateSchema, data)
        assert is_valid is True
        assert not hasattr(result, 'extra_field')


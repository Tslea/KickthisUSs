"""
Test for solution submission workflow via ZIP to Pull Request
"""
import io
import zipfile
import pytest
from unittest.mock import patch, MagicMock
from app.models import Solution, Task


def create_test_zip():
    """Create a simple test ZIP file"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        zf.writestr('test.py', 'print("Hello")')
        zf.writestr('README.md', '# Test Project')
    buffer.seek(0)
    return buffer


def test_submit_solution_endpoint_success(app, db, auth_user, sample_project, sample_task):
    """Test successful solution submission via ZIP"""
    # Get IDs within app context
    with app.app_context():
        user_id = auth_user.id
        project_id = sample_project.id
        task_id = sample_task.id
    
    with app.test_client() as client:
        # Login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
        
        # Mock GitHub Sync Service
        with patch('app.api_uploads.GitHubSyncService') as MockSyncService:
            mock_instance = MockSyncService.return_value
            mock_instance.submit_solution_zip.return_value = {
                'success': True,
                'pr_url': 'https://github.com/test/repo/pull/1',
                'pr_number': 1,
                'branch': 'solution/task-1-testuser',
                'commit_sha': 'abcdef123456'
            }
            
            # Create ZIP file
            zip_buffer = create_test_zip()
            
            # Call API
            response = client.post(
                f'/api/projects/{project_id}/tasks/{task_id}/submit',
                data={'file': (zip_buffer, 'solution.zip')},
                content_type='multipart/form-data'
            )
            
            # Assertions
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'pr_url' in data
            
            # Verify solution was created in DB
            with app.app_context():
                solution = Solution.query.filter_by(task_id=task_id).first()
                assert solution is not None
                assert solution.submitted_by_user_id == user_id
                assert solution.github_pr_number == 1


def test_submit_solution_no_file(app, db, auth_user, sample_project, sample_task):
    """Test submission without file"""
    with app.app_context():
        user_id = auth_user.id
        project_id = sample_project.id
        task_id = sample_task.id
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
        
        response = client.post(
            f'/api/projects/{project_id}/tasks/{task_id}/submit',
            data={},
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False


def test_submit_solution_github_disabled(app, db, auth_user, sample_project, sample_task):
    """Test submission when GitHub sync is disabled"""
    with app.app_context():
        user_id = auth_user.id
        project_id = sample_project.id
        task_id = sample_task.id
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user_id)
            sess['_fresh'] = True
        
        # Mock GitHub sync as unavailable
        with patch('app.api_uploads.GITHUB_SYNC_AVAILABLE', False):
            zip_buffer = create_test_zip()
            
            response = client.post(
                f'/api/projects/{project_id}/tasks/{task_id}/submit',
                data={'file': (zip_buffer, 'solution.zip')},
                content_type='multipart/form-data'
            )
            
            assert response.status_code == 503
            data = response.get_json()
            assert data['success'] is False

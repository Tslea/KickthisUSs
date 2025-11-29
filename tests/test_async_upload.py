import sys
from unittest.mock import MagicMock

# Mock celery module before importing app
mock_celery = MagicMock()
sys.modules['celery'] = mock_celery
sys.modules['celery.result'] = MagicMock()

import unittest
from unittest.mock import patch, MagicMock
import json
import io
import zipfile
from app import create_app, db
from app.models import User, Project
import tasks.github_tasks # Explicit import to register submodule

class TestAsyncUpload(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True, 
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:', 
            'WTF_CSRF_ENABLED': False,
            'SECRET_KEY': 'test-secret-key'
        })
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test user and project
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password')
        db.session.add(self.user)
        db.session.commit()
        
        self.project = Project(name='Test Project', creator_id=self.user.id, category='Tech')
        self.project.github_repo_name = 'test/repo' # Set the actual column
        # Mock the property if it's missing in model but used in code
        # For the purpose of this test, we might need to patch it or assume it exists
        # Let's try to set it dynamically if possible, or rely on github_repo_name if code uses it
        # But code uses github_repo_full_name. 
        # Let's assume for now we just set the column and see if it fails.
        db.session.add(self.project)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch('tasks.github_tasks.sync_workspace_session')
    @patch('app.api_uploads.GITHUB_SYNC_AVAILABLE', True)
    def test_upload_zip_async(self, mock_task):
        # Mock task.delay return value
        mock_task_instance = MagicMock()
        mock_task_instance.id = 'test-task-id'
        mock_task.delay.return_value = mock_task_instance

        # Login
        self.client.post('/auth/login', data={'email': 'test@example.com', 'password': 'password'})

        # Create zip file
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            zf.writestr('test.txt', 'content')
        buffer.seek(0)

        # Upload zip
        response = self.client.post(
            f'/api/projects/{self.project.id}/upload-zip',
            data={'file': (buffer, 'test.zip')},
            content_type='multipart/form-data'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Verify response structure
        self.assertTrue(data['success'])
        self.assertIn('github_sync', data)
        self.assertTrue(data['github_sync']['async'])
        self.assertEqual(data['github_sync']['task_id'], 'test-task-id')
        
        # Verify task was called
        mock_task.delay.assert_called_once()
        args = mock_task.delay.call_args[0]
        self.assertEqual(args[0], self.project.id)
        # args[1] is session_id (random)
        self.assertEqual(args[2], self.user.id)

if __name__ == '__main__':
    unittest.main()

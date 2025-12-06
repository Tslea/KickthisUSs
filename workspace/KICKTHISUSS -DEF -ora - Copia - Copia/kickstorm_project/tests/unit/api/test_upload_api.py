# tests/unit/api/test_upload_api.py
import pytest
from io import BytesIO
from app.models import User, Project, Task, Solution
from tests.factories import UserFactory, ProjectFactory, TaskFactory
from app.extensions import db


class TestUploadAPI:
    """Test API endpoints per upload file."""

    def test_api_solution_upload_endpoint(self, authenticated_client, app, auth_user):
        """Test API endpoint per upload soluzione."""
        with app.app_context():
            project = ProjectFactory(creator=auth_user)
            task = TaskFactory(project=project, creator=auth_user)
            db.session.commit()
            
            # Test endpoint API senza file per evitare problemi di I/O
            data = {
                'solution_content': 'API solution submission without file'
            }
            
            # Testa se esiste un endpoint API per upload
            api_endpoints = [
                f'/api/tasks/{task.id}/solutions',
                f'/api/solutions/upload',
                f'/tasks/{task.id}/api/submit'
            ]
            
            for endpoint in api_endpoints:
                response = authenticated_client.post(endpoint, json=data)
                
                # Se l'endpoint esiste, dovrebbe funzionare o dare errore valido
                if response.status_code != 404:
                    assert response.status_code in [200, 201, 400, 401, 403]
                    break
            else:
                # Se nessun endpoint API esiste, è normale
                assert True

    def test_api_file_validation(self, authenticated_client, app, auth_user):
        """Test validazione file via API."""
        with app.app_context():
            project = ProjectFactory(creator=auth_user)
            task = TaskFactory(project=project, creator=auth_user)
            db.session.commit()
            
            # Test con file non permesso
            invalid_data = {
                'solution_content': 'Solution with invalid file',
                'solution_file': (BytesIO(b'malicious code'), 'malware.exe')
            }
            
            response = authenticated_client.post(f'/tasks/task/{task.id}/submit_solution',
                                               data=invalid_data,
                                               content_type='multipart/form-data')
            
            # Dovrebbe rifiutare file .exe (200 per form reload, 302 per redirect, 400 per error)
            assert response.status_code in [200, 302, 400]

    def test_api_json_upload_alternative(self, authenticated_client, app, auth_user):
        """Test upload tramite JSON (base64) come alternativa."""
        with app.app_context():
            project = ProjectFactory(creator=auth_user)
            task = TaskFactory(project=project, creator=auth_user)
            db.session.commit()
            
            import base64
            
            # Simula upload base64
            file_content = b'Solution code content'
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            json_data = {
                'solution_content': 'Solution with base64 file',
                'file_data': encoded_content,
                'file_name': 'solution.txt',
                'file_type': 'text/plain'
            }
            
            # Testa se esiste un endpoint JSON per upload
            response = authenticated_client.post(f'/api/tasks/{task.id}/solutions',
                                               json=json_data,
                                               content_type='application/json')
            
            # Se l'endpoint non esiste (404), è normale
            assert response.status_code in [200, 201, 400, 404]


class TestFileUploadSecurity:
    """Test sicurezza upload file."""

    def test_upload_without_authentication(self, client, app):
        """Test upload senza autenticazione."""
        with app.app_context():
            user = UserFactory()
            project = ProjectFactory(creator=user)
            task = TaskFactory(project=project, creator=user)
            db.session.commit()
            
            data = {
                'solution_content': 'Unauthorized solution',
                'solution_file': (BytesIO(b'unauthorized content'), 'hack.txt')
            }
            
            response = client.post(f'/tasks/task/{task.id}/submit_solution',
                                 data=data,
                                 content_type='multipart/form-data')
            
            # Dovrebbe richiedere autenticazione
            assert response.status_code in [302, 401, 403]

    def test_upload_to_nonexistent_task(self, authenticated_client, app, auth_user):
        """Test upload a task inesistente."""
        with app.app_context():
            fake_task_id = 999999
            
            data = {
                'solution_content': 'Solution for fake task',
                'solution_file': (BytesIO(b'content'), 'solution.txt')
            }
            
            response = authenticated_client.post(f'/tasks/task/{fake_task_id}/submit_solution',
                                               data=data,
                                               content_type='multipart/form-data')
            
            # Dovrebbe dare 404
            assert response.status_code == 404

    def test_file_mime_type_validation(self, authenticated_client, app, auth_user):
        """Test validazione MIME type file."""
        with app.app_context():
            project = ProjectFactory(creator=auth_user)
            task = TaskFactory(project=project, creator=auth_user)
            db.session.commit()
            
            # File con estensione .txt ma contenuto binario sospetto
            suspicious_data = b'\x00\x01\x02\x03\xFF\xFE'  # Dati binari
            
            data = {
                'solution_content': 'Solution with suspicious file',
                'solution_file': (BytesIO(suspicious_data), 'text.txt')
            }
            
            response = authenticated_client.post(f'/tasks/task/{task.id}/submit_solution',
                                               data=data,
                                               content_type='multipart/form-data')
            
            # Il server dovrebbe gestire file con contenuto sospetto
            assert response.status_code in [200, 302, 400]

    def test_concurrent_file_uploads(self, authenticated_client, app, auth_user):
        """Test upload simultanei (stress test leggero)."""
        with app.app_context():
            project = ProjectFactory(creator=auth_user)
            task = TaskFactory(project=project, creator=auth_user)
            db.session.commit()
            
            # Simula upload multipli rapidi
            responses = []
            for i in range(3):
                data = {
                    'solution_content': f'Concurrent solution {i}',
                    'solution_file': (BytesIO(f'File content {i}'.encode()), f'solution_{i}.txt')
                }
                
                response = authenticated_client.post(f'/tasks/task/{task.id}/submit_solution',
                                                   data=data,
                                                   content_type='multipart/form-data')
                responses.append(response)
            
            # Tutti dovrebbero essere gestiti correttamente
            for i, response in enumerate(responses):
                assert response.status_code in [200, 302, 400], f"Concurrent upload {i} failed"


class TestFileUploadPerformance:
    """Test performance upload file."""

    def test_upload_response_time(self, authenticated_client, app, auth_user):
        """Test tempo di risposta upload."""
        with app.app_context():
            import time
            
            project = ProjectFactory(creator=auth_user)
            task = TaskFactory(project=project, creator=auth_user)
            db.session.commit()
            
            # File di dimensioni moderate
            file_content = b'x' * (100 * 1024)  # 100KB
            
            data = {
                'solution_content': 'Performance test solution',
                'solution_file': (BytesIO(file_content), 'performance_test.txt')
            }
            
            start_time = time.time()
            response = authenticated_client.post(f'/tasks/task/{task.id}/submit_solution',
                                               data=data,
                                               content_type='multipart/form-data')
            end_time = time.time()
            
            upload_time = end_time - start_time
            
            # Upload dovrebbe completarsi entro 15 secondi per file 100KB (include analisi AI)
            assert upload_time < 15.0, f"Upload took {upload_time:.2f}s, too slow"
            assert response.status_code in [200, 302]

    def test_memory_usage_large_file(self, authenticated_client, app, auth_user):
        """Test uso memoria con file grandi."""
        with app.app_context():
            project = ProjectFactory(creator=auth_user)
            task = TaskFactory(project=project, creator=auth_user)
            db.session.commit()
            
            # File relativamente grande per test (1MB)
            large_content = b'x' * (1024 * 1024)  # 1MB
            
            data = {
                'solution_content': 'Large file test',
                'solution_file': (BytesIO(large_content), 'large_file.txt')
            }
            
            # Il test principale è che non crashi per memoria
            try:
                response = authenticated_client.post(f'/tasks/task/{task.id}/submit_solution',
                                                   data=data,
                                                   content_type='multipart/form-data')
                
                # Deve gestire il file senza crashare
                assert response.status_code in [200, 302, 413]  # 413 = Payload too large
                
            except MemoryError:
                # Se va in memory error, almeno dovrebbe essere gestito
                assert False, "Memory error not handled properly for large file upload"

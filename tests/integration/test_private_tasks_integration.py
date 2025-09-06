# tests/integration/test_private_tasks_integration.py
"""
Test di integrazione per la funzionalità dei task privati
"""

import pytest
from flask import url_for
from app.models import User, Project, Task, Collaborator
from tests.factories import UserFactory, ProjectFactory


class TestPrivateTasksIntegration:
    """Test di integrazione per task privati"""

    def test_create_private_task_as_creator(self, client, app, db):
        """Test creazione task privato da parte del creatore del progetto"""
        with app.app_context():
            # Crea utente e progetto
            creator = UserFactory()
            creator.set_password('testpassword')
            project = ProjectFactory(creator=creator)
            db.session.commit()
            
            # Login del creatore
            client.post('/auth/login', data={
                'email': creator.email,
                'password': 'testpassword'
            })
            
            # Crea task privato
            response = client.post(f'/tasks/project/{project.id}/add_task', data={
                'title': 'Task Privato Test',
                'description': 'Questo è un task privato per il team interno',
                'task_type': 'implementation',
                'phase': 'planning',
                'difficulty': 'medium',
                'equity_reward': 2.5,
                'is_private': True,
                'csrf_token': 'test-token'
            })
            
            # Verifica che il task sia stato creato
            assert response.status_code in [200, 302]  # Success or redirect
            
            # Verifica che il task sia nel database
            task = Task.query.filter_by(title='Task Privato Test').first()
            assert task is not None
            assert task.is_private == True
            assert task.project_id == project.id

    def test_create_private_task_as_collaborator(self, client, app, db):
        """Test creazione task privato da parte di un collaboratore"""
        with app.app_context():
            # Crea utenti
            creator = UserFactory()
            collaborator_user = UserFactory()
            collaborator_user.set_password('testpassword')
            
            # Crea progetto
            project = ProjectFactory(creator=creator)
            
            # Aggiungi collaboratore
            collaborator = Collaborator(
                project_id=project.id,
                user_id=collaborator_user.id,
                role='collaborator',
                equity_share=5.0
            )
            db.session.add(collaborator)
            db.session.commit()
            
            # Login del collaboratore
            client.post('/auth/login', data={
                'email': collaborator_user.email,
                'password': 'testpassword'
            })
            
            # Crea task privato
            response = client.post(f'/tasks/project/{project.id}/add_task', data={
                'title': 'Task Privato Collaboratore',
                'description': 'Task privato creato dal collaboratore',
                'task_type': 'implementation',
                'phase': 'planning',
                'difficulty': 'medium',
                'equity_reward': 2.0,
                'is_private': True,
                'csrf_token': 'test-token'
            })
            
            # Verifica che il task sia stato creato
            assert response.status_code in [200, 302]
            
            # Verifica nel database
            task = Task.query.filter_by(title='Task Privato Collaboratore').first()
            assert task is not None
            assert task.is_private == True

    def test_regular_user_cannot_create_private_task(self, client, app, db):
        """Test che un utente normale non possa creare task privati"""
        with app.app_context():
            # Crea utenti
            creator = UserFactory()
            regular_user = UserFactory()
            regular_user.set_password('testpassword')
            
            # Crea progetto
            project = ProjectFactory(creator=creator)
            db.session.commit()
            
            # Login dell'utente normale
            client.post('/auth/login', data={
                'email': regular_user.email,
                'password': 'testpassword'
            })
            
            # Prova a creare task privato (dovrebbe fallire)
            response = client.post(f'/tasks/project/{project.id}/add_task', data={
                'title': 'Task Privato Non Autorizzato',
                'description': 'Questo non dovrebbe essere creato',
                'task_type': 'implementation',
                'phase': 'planning',
                'difficulty': 'medium',
                'equity_reward': 2.0,
                'is_private': True,
                'csrf_token': 'test-token'
            })
            
            # Dovrebbe essere negato l'accesso (403) o reindirizzato
            assert response.status_code in [403, 302]

    def test_private_task_visibility_in_project_view(self, client, app, db):
        """Test che i task privati siano visibili solo agli utenti autorizzati nella vista progetto"""
        with app.app_context():
            # Crea utenti
            creator = UserFactory()
            creator.set_password('testpassword')
            collaborator_user = UserFactory()
            collaborator_user.set_password('collabpassword')
            regular_user = UserFactory()
            regular_user.set_password('regularpassword')
            
            # Crea progetto
            project = ProjectFactory(creator=creator)
            
            # Aggiungi collaboratore
            collaborator = Collaborator(
                project_id=project.id,
                user_id=collaborator_user.id,
                role='collaborator',
                equity_share=5.0
            )
            db.session.add(collaborator)
            
            # Crea mix di task pubblici e privati
            public_task = Task(
                project_id=project.id,
                creator_id=creator.id,
                title="Task Pubblico",
                description="Questo task è pubblico",
                equity_reward=1.0,
                task_type="implementation",
                phase="planning",
                difficulty="easy",
                is_private=False
            )
            
            private_task = Task(
                project_id=project.id,
                creator_id=creator.id,
                title="Task Privato",
                description="Questo task è privato",
                equity_reward=2.0,
                task_type="implementation",
                phase="planning", 
                difficulty="medium",
                is_private=True
            )
            
            db.session.add_all([public_task, private_task])
            db.session.commit()
            
            # Test vista progetto per il creatore
            client.post('/auth/login', data={
                'email': creator.email,
                'password': 'testpassword'
            })
            response = client.get(f'/project/{project.id}')
            assert response.status_code == 200
            response_text = response.get_data(as_text=True)
            assert "Task Pubblico" in response_text
            assert "Task Privato" in response_text  # Creatore vede tutti i task
            
            # Logout e login come collaboratore
            client.get('/auth/logout')
            client.post('/auth/login', data={
                'email': collaborator_user.email,
                'password': 'collabpassword'
            })
            response = client.get(f'/project/{project.id}')
            assert response.status_code == 200
            response_text = response.get_data(as_text=True)
            assert "Task Pubblico" in response_text
            assert "Task Privato" in response_text  # Collaboratore vede tutti i task
            
            # Logout e login come utente normale
            client.get('/auth/logout')
            client.post('/auth/login', data={
                'email': regular_user.email,
                'password': 'regularpassword'
            })
            response = client.get(f'/project/{project.id}')
            assert response.status_code == 200
            response_text = response.get_data(as_text=True)
            assert "Task Pubblico" in response_text
            assert "Task Privato" not in response_text  # Utente normale non vede task privati

    def test_private_task_badge_display(self, client, app, db):
        """Test che il badge 'Privato' sia mostrato sui task privati"""
        with app.app_context():
            # Crea utente e progetto
            creator = UserFactory()
            creator.set_password('testpassword')
            project = ProjectFactory(creator=creator)
            
            # Crea task privato
            private_task = Task(
                project_id=project.id,
                creator_id=creator.id,
                title="Task con Badge Privato",
                description="Task per testare il badge",
                equity_reward=1.5,
                task_type="implementation",
                phase="planning",
                difficulty="easy",
                is_private=True
            )
            
            db.session.add(private_task)
            db.session.commit()
            
            # Login e visualizza progetto
            client.post('/auth/login', data={
                'email': creator.email,
                'password': 'testpassword'
            })
            response = client.get(f'/project/{project.id}')
            assert response.status_code == 200
            response_text = response.get_data(as_text=True)
            
            # Verifica che il badge "Privato" sia presente
            assert "Privato" in response_text
            assert "lock" in response_text  # Icona del lucchetto

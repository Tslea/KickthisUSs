# tests/unit/models/test_private_tasks.py
"""
Test per la funzionalità dei task privati
"""

import pytest
from app.models import User, Project, Task, Collaborator
from tests.factories import UserFactory, ProjectFactory, TaskFactory


class TestPrivateTaskPermissions:
    """Test per i permessi dei task privati"""

    def test_public_task_visible_to_everyone(self, app, db):
        """Test che i task pubblici siano visibili a tutti"""
        with app.app_context():
            # Crea utenti
            creator = UserFactory()
            regular_user = UserFactory()
            
            # Crea progetto
            project = ProjectFactory(creator=creator)
            
            # Crea task pubblico
            task = TaskFactory(project=project, creator=creator, is_private=False)
            db.session.commit()
            
            # Test che il task sia visibile a tutti
            assert task.can_view(creator) == True
            assert task.can_view(regular_user) == True
            assert task.can_view(None) == True  # Utente non autenticato

    def test_private_task_visible_only_to_authorized_users(self, app, db):
        """Test che i task privati siano visibili solo a creatore e collaboratori"""
        with app.app_context():
            # Crea utenti
            creator = UserFactory()
            collaborator_user = UserFactory()
            regular_user = UserFactory()
            
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
            
            # Crea task privato
            task = TaskFactory(project=project, creator=creator, is_private=True)
            db.session.commit()
            
            # Test visibilità
            assert task.can_view(creator) == True  # Creatore può vedere
            assert task.can_view(collaborator_user) == True  # Collaboratore può vedere
            assert task.can_view(regular_user) == False  # Utente normale non può vedere
            assert task.can_view(None) == False  # Utente non autenticato non può vedere

    def test_task_creation_permissions(self, app, db):
        """Test che solo creatore e collaboratori possano creare task privati"""
        with app.app_context():
            # Crea utenti
            creator = UserFactory()
            collaborator_user = UserFactory()
            regular_user = UserFactory()
            
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
            
            # Test permessi di creazione
            assert Task.can_create_for_project(project, creator) == True
            assert Task.can_create_for_project(project, collaborator_user) == True
            assert Task.can_create_for_project(project, regular_user) == False
            assert Task.can_create_for_project(project, None) == False

    def test_private_task_creation_workflow(self, app, db):
        """Test completo del workflow di creazione task privato"""
        with app.app_context():
            # Crea utenti
            creator = UserFactory()
            collaborator_user = UserFactory()
            
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
            
            # Crea task privato dal collaboratore
            private_task = Task(
                project_id=project.id,
                creator_id=collaborator_user.id,
                title="Task Privato di Sviluppo",
                description="Questo è un task interno per lo sviluppo",
                equity_reward=2.0,
                task_type="implementation",
                is_private=True
            )
            db.session.add(private_task)
            db.session.commit()
            
            # Verifica che il task sia stato creato correttamente
            assert private_task.is_private == True
            assert private_task.can_view(creator) == True
            assert private_task.can_view(collaborator_user) == True

    def test_private_task_default_value(self, app, db):
        """Test che il valore default di is_private sia False"""
        with app.app_context():
            creator = UserFactory()
            project = ProjectFactory(creator=creator)
            
            # Crea task senza specificare is_private
            task = TaskFactory(project=project, creator=creator)
            db.session.commit()
            
            # Verifica che il default sia False (task pubblico)
            assert task.is_private == False

    def test_mixed_tasks_filtering(self, app, db):
        """Test che il filtraggio funzioni con una mix di task pubblici e privati"""
        with app.app_context():
            # Crea utenti
            creator = UserFactory()
            collaborator_user = UserFactory()
            regular_user = UserFactory()
            
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
            
            # Crea mix di task
            public_task1 = TaskFactory(project=project, creator=creator, is_private=False)
            private_task1 = TaskFactory(project=project, creator=creator, is_private=True)
            public_task2 = TaskFactory(project=project, creator=collaborator_user, is_private=False)
            private_task2 = TaskFactory(project=project, creator=collaborator_user, is_private=True)
            
            db.session.commit()
            
            # Test filtraggio per diversi utenti
            all_tasks = [public_task1, private_task1, public_task2, private_task2]
            
            # Creatore vede tutti i task
            creator_visible_tasks = [task for task in all_tasks if task.can_view(creator)]
            assert len(creator_visible_tasks) == 4
            
            # Collaboratore vede tutti i task
            collaborator_visible_tasks = [task for task in all_tasks if task.can_view(collaborator_user)]
            assert len(collaborator_visible_tasks) == 4
            
            # Utente normale vede solo i task pubblici
            regular_visible_tasks = [task for task in all_tasks if task.can_view(regular_user)]
            assert len(regular_visible_tasks) == 2
            assert public_task1 in regular_visible_tasks
            assert public_task2 in regular_visible_tasks
            assert private_task1 not in regular_visible_tasks
            assert private_task2 not in regular_visible_tasks

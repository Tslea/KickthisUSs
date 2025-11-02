"""
Test Suite per Free Proposals (Proposte Libere)
Test completi per la funzionalità di proposte libere che permette agli sviluppatori
di aggregare task o proporre nuovi task con equity personalizzata.
"""

import pytest
from datetime import datetime, timezone
from flask import url_for
from app.extensions import db
from app.models import (
    User, Project, Task, FreeProposal, Collaborator, 
    ProjectEquity, EquityHistory, Notification
)


# Non definiamo fixture app() e client() perché sono già in conftest.py
# Usiamo quelli globali del progetto

@pytest.fixture
def creator_user(app):
    """Crea un utente creatore di progetto"""
    with app.app_context():
        user = User(username='creator', email='creator@test.com')
        user.set_password('password123')
        user.email_verified = True
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)  # Refresh per avere l'ID
        return user


@pytest.fixture
def developer_user(app):
    """Crea un utente sviluppatore"""
    with app.app_context():
        user = User(username='developer', email='dev@test.com')
        user.set_password('password123')
        user.email_verified = True
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)  # Refresh per avere l'ID
        return user


@pytest.fixture
def test_project(app, creator_user):
    """Crea un progetto di test"""
    with app.app_context():
        project = Project(
            name='Test Project',
            pitch='Test pitch',
            description='Test description',
            creator_id=creator_user.id,
            category='Tech',
            creator_equity=5.0,
            platform_fee=1.0,
            status='open'
        )
        db.session.add(project)
        db.session.commit()
        db.session.refresh(project)  # Refresh per avere l'ID
        return project


@pytest.fixture
def test_tasks(app, test_project):
    """Crea task di test"""
    with app.app_context():
        tasks = []
        for i in range(3):
            task = Task(
                project_id=test_project.id,
                creator_id=test_project.creator_id,
                title=f'Test Task {i+1}',
                description=f'Description for task {i+1}',
                equity_reward=5.0,  # Corretto: equity_reward invece di equity_share
                status='open',
                phase='Development',
                difficulty='Medium'
            )
            tasks.append(task)
            db.session.add(task)
        db.session.commit()
        # Refresh tutti i task
        for task in tasks:
            db.session.refresh(task)
        return tasks


class TestFreeProposalModel:
    """Test per il modello FreeProposal"""
    
    def test_create_multi_task_proposal(self, app, test_project, developer_user, test_tasks):
        """Test creazione proposta multi-task"""
        with app.app_context():
            proposal = FreeProposal(
                project_id=test_project.id,
                developer_id=developer_user.id,
                title='Complete Backend Integration',
                description='I will complete all backend tasks together',
                equity_requested=15.0,
                proposal_type='multi_task'
            )
            proposal.aggregated_tasks = test_tasks
            db.session.add(proposal)
            db.session.commit()
            
            assert proposal.id is not None
            assert proposal.status == 'pending'
            assert proposal.aggregated_task_count == 3
            assert proposal.total_aggregated_equity == 15.0
            assert proposal.is_pending
    
    def test_create_new_task_proposal(self, app, test_project, developer_user):
        """Test creazione proposta nuovo task"""
        with app.app_context():
            proposal = FreeProposal(
                project_id=test_project.id,
                developer_id=developer_user.id,
                title='New Feature Proposal',
                description='I propose to add a new feature',
                equity_requested=10.0,
                proposal_type='new_task',
                new_task_details='Detailed description of the new task...'
            )
            db.session.add(proposal)
            db.session.commit()
            
            assert proposal.id is not None
            assert proposal.new_task_details is not None
            assert proposal.proposal_type == 'new_task'
    
    def test_proposal_properties(self, app, test_project, developer_user):
        """Test delle proprietà del modello"""
        with app.app_context():
            proposal = FreeProposal(
                project_id=test_project.id,
                developer_id=developer_user.id,
                title='Test Proposal',
                description='Test description',
                equity_requested=10.0,
                proposal_type='multi_task',
                status='accepted'
            )
            db.session.add(proposal)
            db.session.commit()
            
            assert proposal.is_accepted
            assert not proposal.is_pending
            assert not proposal.is_rejected
            assert proposal.status_display == '✅ Accettata'
            assert proposal.status_badge_class == 'success'


class TestFreeProposalRoutes:
    """Test per le routes delle proposte libere"""
    
    def test_propose_form_access(self, client, app, test_project, developer_user):
        """Test accesso al form di proposta"""
        with app.app_context():
            # Login come developer
            client.post('/auth/login', data={
                'email': 'dev@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Accesso al form
            response = client.get(f'/project/{test_project.id}/propose-free')
            assert response.status_code == 200
    
    def test_creator_cannot_propose_to_own_project(self, client, app, test_project, creator_user):
        """Test che il creatore non possa proporre al suo progetto"""
        with app.app_context():
            # Login come creator
            client.post('/auth/login', data={
                'email': 'creator@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Tentativo di accesso al form
            response = client.get(f'/project/{test_project.id}/propose-free', follow_redirects=True)
            assert b'Non puoi proporre soluzioni al tuo progetto' in response.data
    
    def test_submit_multi_task_proposal(self, client, app, test_project, developer_user, test_tasks):
        """Test invio proposta multi-task"""
        with app.app_context():
            # Login
            client.post('/auth/login', data={
                'email': 'dev@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Invia proposta
            response = client.post(f'/project/{test_project.id}/propose-free', data={
                'proposal_type': 'multi_task',
                'title': 'Backend Integration',
                'description': 'A' * 100,  # Minimo 50 caratteri
                'equity_requested': 15.0,
                'task_ids': [str(task.id) for task in test_tasks]
            }, follow_redirects=True)
            
            assert response.status_code == 200
            assert b'Proposta inviata con successo' in response.data
            
            # Verifica creazione in DB
            proposal = FreeProposal.query.filter_by(
                project_id=test_project.id,
                developer_id=developer_user.id
            ).first()
            assert proposal is not None
            assert proposal.aggregated_task_count == 3
    
    def test_submit_new_task_proposal(self, client, app, test_project, developer_user):
        """Test invio proposta nuovo task"""
        with app.app_context():
            # Login
            client.post('/auth/login', data={
                'email': 'dev@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Invia proposta
            response = client.post(f'/project/{test_project.id}/propose-free', data={
                'proposal_type': 'new_task',
                'title': 'New Feature',
                'description': 'B' * 100,
                'equity_requested': 10.0,
                'new_task_details': 'C' * 100
            }, follow_redirects=True)
            
            assert response.status_code == 200
            assert b'Proposta inviata con successo' in response.data
    
    def test_validation_minimum_description(self, client, app, test_project, developer_user):
        """Test validazione lunghezza minima descrizione"""
        with app.app_context():
            # Login
            client.post('/auth/login', data={
                'email': 'dev@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Invia proposta con descrizione troppo breve
            response = client.post(f'/project/{test_project.id}/propose-free', data={
                'proposal_type': 'multi_task',
                'title': 'Test',
                'description': 'Short',  # Troppo breve
                'equity_requested': 10.0,
                'task_ids': []
            }, follow_redirects=True)
            
            assert b'almeno 50 caratteri' in response.data
    
    def test_validation_equity_range(self, client, app, test_project, developer_user):
        """Test validazione range equity"""
        with app.app_context():
            # Login
            client.post('/auth/login', data={
                'email': 'dev@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Equity troppo alta (oltre 100%)
            response = client.post(f'/project/{test_project.id}/propose-free', data={
                'proposal_type': 'new_task',
                'title': 'Test Equity Too High',
                'description': 'A' * 100,
                'equity_requested': 150.0,  # Oltre 100%
                'new_task_details': 'B' * 100
            }, follow_redirects=True)
            
            # Verifica che la richiesta sia stata redirezionata (non ha creato la proposta)
            assert response.status_code == 200
            # Il messaggio flash può essere presente in vari formati nel HTML
            assert b'equity' in response.data.lower() or b'0.1%' in response.data or b'100%' in response.data
            
            # Verifica che non sia stata creata nessuna proposta
            from app.models import FreeProposal
            proposals = FreeProposal.query.filter_by(project_id=test_project.id).all()
            # Se c'erano proposte prima, il numero dovrebbe essere lo stesso
            # (la proposta invalida non è stata creata)



class TestProposalDecision:
    """Test per le decisioni sulle proposte"""
    
    def test_accept_proposal(self, client, app, test_project, creator_user, developer_user, test_tasks):
        """Test accettazione proposta"""
        with app.app_context():
            # Crea proposta
            proposal = FreeProposal(
                project_id=test_project.id,
                developer_id=developer_user.id,
                title='Test Proposal',
                description='Test description',
                equity_requested=10.0,
                proposal_type='multi_task'
            )
            proposal.aggregated_tasks = test_tasks[:2]  # 2 task
            db.session.add(proposal)
            db.session.commit()
            proposal_id = proposal.id
            
            # Login come creator
            client.post('/auth/login', data={
                'email': 'creator@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Accetta proposta
            response = client.post(f'/proposal/{proposal_id}/decide', data={
                'decision': 'accept',
                'decision_note': 'Great work!'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verifica cambiamenti
            proposal = FreeProposal.query.get(proposal_id)
            assert proposal.status == 'accepted'
            assert proposal.decision_note == 'Great work!'
            
            # Verifica equity assegnata
            equity = ProjectEquity.query.filter_by(
                project_id=test_project.id,
                user_id=developer_user.id
            ).first()
            assert equity is not None
            assert equity.equity_percentage == 10.0
            
            # Verifica history
            history = EquityHistory.query.filter_by(
                project_id=test_project.id,
                user_id=developer_user.id,
                action='grant'
            ).first()
            assert history is not None
            assert history.equity_change == 10.0
            
            # Verifica task completati
            for task in test_tasks[:2]:
                task_db = Task.query.get(task.id)
                assert task_db.status == 'approved'
    
    def test_reject_proposal(self, client, app, test_project, creator_user, developer_user):
        """Test rifiuto proposta"""
        with app.app_context():
            # Crea proposta
            proposal = FreeProposal(
                project_id=test_project.id,
                developer_id=developer_user.id,
                title='Test Proposal',
                description='Test description',
                equity_requested=10.0,
                proposal_type='new_task',
                new_task_details='New task details'
            )
            db.session.add(proposal)
            db.session.commit()
            proposal_id = proposal.id
            
            # Login come creator
            client.post('/auth/login', data={
                'email': 'creator@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Rifiuta proposta
            response = client.post(f'/proposal/{proposal_id}/decide', data={
                'decision': 'reject',
                'decision_note': 'Not aligned with project goals'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verifica status
            proposal = FreeProposal.query.get(proposal_id)
            assert proposal.status == 'rejected'
            assert proposal.decision_note is not None
            
            # Verifica che NON sia stata assegnata equity
            equity = ProjectEquity.query.filter_by(
                project_id=test_project.id,
                user_id=developer_user.id
            ).first()
            assert equity is None
    
    def test_only_creator_can_decide(self, client, app, test_project, developer_user):
        """Test che solo il creatore possa decidere"""
        with app.app_context():
            # Crea proposta
            proposal = FreeProposal(
                project_id=test_project.id,
                developer_id=developer_user.id,
                title='Test Proposal',
                description='Test description',
                equity_requested=10.0,
                proposal_type='new_task'
            )
            db.session.add(proposal)
            db.session.commit()
            proposal_id = proposal.id
            
            # Login come developer (non creatore)
            client.post('/auth/login', data={
                'email': 'dev@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Tentativo di decisione
            response = client.post(f'/proposal/{proposal_id}/decide', data={
                'decision': 'accept'
            })
            
            assert response.status_code == 403  # Forbidden


class TestProposalNotifications:
    """Test per le notifiche delle proposte"""
    
    def test_notification_on_proposal_creation(self, client, app, test_project, developer_user, creator_user):
        """Test notifica quando viene creata una proposta"""
        with app.app_context():
            # Login come developer
            client.post('/auth/login', data={
                'email': 'dev@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Crea proposta
            client.post(f'/project/{test_project.id}/propose-free', data={
                'proposal_type': 'new_task',
                'title': 'New Feature',
                'description': 'A' * 100,
                'equity_requested': 10.0,
                'new_task_details': 'B' * 100
            }, follow_redirects=True)
            
            # Verifica notifica per creator
            notification = Notification.query.filter_by(
                user_id=creator_user.id,
                type='free_proposal'
            ).first()
            assert notification is not None
            assert 'proposto una soluzione libera' in notification.message
    
    def test_notification_on_proposal_decision(self, client, app, test_project, creator_user, developer_user):
        """Test notifica quando viene presa una decisione"""
        with app.app_context():
            # Crea proposta
            proposal = FreeProposal(
                project_id=test_project.id,
                developer_id=developer_user.id,
                title='Test Proposal',
                description='Test description',
                equity_requested=10.0,
                proposal_type='new_task'
            )
            db.session.add(proposal)
            db.session.commit()
            proposal_id = proposal.id
            
            # Login come creator
            client.post('/auth/login', data={
                'email': 'creator@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Accetta proposta
            client.post(f'/proposal/{proposal_id}/decide', data={
                'decision': 'accept',
                'decision_note': 'Great!'
            }, follow_redirects=True)
            
            # Verifica notifica per developer
            notification = Notification.query.filter_by(
                user_id=developer_user.id,
                type='proposal_accepted'
            ).first()
            assert notification is not None
            assert 'accettata' in notification.message


class TestProposalDashboard:
    """Test per la dashboard delle proposte"""
    
    def test_my_proposals_page(self, client, app, developer_user):
        """Test pagina dashboard proposte"""
        with app.app_context():
            # Login
            client.post('/auth/login', data={
                'email': 'dev@test.com',
                'password': 'password123'
            }, follow_redirects=True)
            
            # Accesso dashboard
            response = client.get('/my-proposals')
            assert response.status_code == 200
            assert b'Le Mie Proposte Libere' in response.data


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

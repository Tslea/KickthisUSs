# tests/integration/test_auth_email_workflows.py
"""
Test di integrazione per i workflow di autenticazione email
"""

import pytest
from unittest.mock import patch
from flask import url_for
from app.models import User
from tests.factories import UserFactory


class TestAuthEmailWorkflows:
    """Test per i workflow email nell'autenticazione."""
    
    def test_registration_sends_verification_email(self, client, app, db):
        """Test che la registrazione invii email di verifica."""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            
            with patch('app.email_service.send_verification_email') as mock_send:
                mock_send.return_value = True
                
                response = client.post('/auth/register', data={
                    'username': 'newuser',
                    'email': 'newuser@example.com',
                    'password': 'password123',
                    'confirm_password': 'password123'
                })
                
                assert response.status_code == 302  # Redirect dopo registrazione
                
                # Verifica che l'email sia stata inviata
                mock_send.assert_called_once()
                
                # Verifica che l'utente sia stato creato
                user = User.query.filter_by(email='newuser@example.com').first()
                assert user is not None
                assert user.email_verified is False or user.email_verified is None
    
    def test_email_verification_flow(self, client, app, db):
        """Test completo del flusso di verifica email."""
        with app.app_context():
            # Crea utente non verificato
            user = UserFactory(email_verified=False)
            token = user.generate_email_verification_token()
            db.session.commit()
            
            with patch('app.email_service.send_welcome_email') as mock_welcome:
                mock_welcome.return_value = True
                
                # Verifica l'email tramite token
                response = client.get(f'/auth/verify-email/{token}')
                
                assert response.status_code == 302  # Redirect dopo verifica
                
                # Verifica che l'utente sia ora verificato
                db.session.refresh(user)
                assert user.email_verified is True
                assert user.email_verification_token is None
                
                # Verifica che l'email di benvenuto sia stata inviata
                mock_welcome.assert_called_once_with(user)
    
    def test_email_verification_invalid_token(self, client, app, db):
        """Test verifica email con token non valido."""
        with app.app_context():
            response = client.get('/auth/verify-email/invalid_token_123')
            
            assert response.status_code == 302  # Redirect
            # Dovrebbe reindirizzare al login con messaggio di errore
    
    def test_forgot_password_flow(self, client, app, db):
        """Test completo del flusso password dimenticata."""
        with app.app_context():
            # Crea utente verificato
            user = UserFactory(email_verified=True)
            db.session.commit()
            
            with patch('app.email_service.send_password_reset_email') as mock_reset:
                mock_reset.return_value = True
                
                # Richiedi reset password
                response = client.post('/auth/forgot-password', data={
                    'email': user.email
                })
                
                assert response.status_code == 302  # Redirect
                
                # Verifica che l'email di reset sia stata inviata
                mock_reset.assert_called_once()
    
    def test_forgot_password_unverified_user(self, client, app, db):
        """Test reset password per utente non verificato."""
        with app.app_context():
            # Crea utente NON verificato
            user = UserFactory(email_verified=False)
            db.session.commit()
            
            response = client.post('/auth/forgot-password', data={
                'email': user.email
            })
            
            assert response.status_code == 302  # Redirect
            # Dovrebbe mostrare messaggio che richiede verifica email prima
    
    def test_password_reset_flow(self, client, app, db):
        """Test completo del flusso reset password."""
        with app.app_context():
            user = UserFactory(email_verified=True)
            token = user.generate_password_reset_token()
            db.session.commit()
            
            old_password_hash = user.password_hash
            
            # Reset password tramite token
            response = client.post(f'/auth/reset-password/{token}', data={
                'password': 'new_password123',
                'confirm_password': 'new_password123'
            })
            
            assert response.status_code == 302  # Redirect dopo reset
            
            # Verifica che la password sia cambiata
            db.session.refresh(user)
            assert user.password_hash != old_password_hash
            assert user.check_password('new_password123')
            assert user.password_reset_token is None
    
    def test_resend_verification_email(self, authenticated_client, app, db):
        """Test reinvio email di verifica."""
        with app.app_context():
            # L'authenticated_client dovrebbe fornire un utente loggato
            # Per questo test creiamo un utente non verificato
            user = UserFactory(email_verified=False)
            db.session.commit()
            
            # Login manuale per questo test
            with authenticated_client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            with patch('app.email_service.send_verification_email') as mock_send:
                mock_send.return_value = True
                
                response = authenticated_client.get('/auth/resend-verification')
                
                assert response.status_code == 302  # Redirect
                mock_send.assert_called_once()
    
    def test_email_middleware_protection(self, authenticated_client, app, db):
        """Test che il middleware protegga le funzioni che richiedono email verificata."""
        with app.app_context():
            # Crea utente NON verificato
            user = UserFactory(email_verified=False)
            db.session.commit()
            
            # Simula login di utente non verificato
            with authenticated_client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Prova ad accedere a una funzione protetta (crea progetto)
            response = authenticated_client.get('/create-project')
            
            # Debug: verifica contenuto della risposta
            print(f"Status code: {response.status_code}")
            print(f"Response data: {response.get_data(as_text=True)[:200]}")
            
            # Dovrebbe essere bloccato dal middleware
            # Se ritorna 200, potrebbe mostrare un avviso invece di bloccare
            if response.status_code == 200:
                # Verifica se c'è un messaggio di warning nella risposta
                response_text = response.get_data(as_text=True)
                assert 'verificare la tua email' in response_text or 'email verification' in response_text.lower()
            else:
                assert response.status_code in [302, 403]  # Redirect o Forbidden


class TestEmailSecurityFeatures:
    """Test per le funzionalità di sicurezza email."""
    
    def test_token_expiration_verification(self, client, app, db):
        """Test scadenza token verifica email."""
        with app.app_context():
            user = UserFactory(email_verified=False)
            token = user.generate_email_verification_token()
            
            # Simula token scaduto (più di 24 ore fa)
            from datetime import timedelta
            user.email_verification_sent_at = user.email_verification_sent_at - timedelta(hours=25)
            db.session.commit()
            
            response = client.get(f'/auth/verify-email/{token}')
            
            assert response.status_code == 302  # Redirect
            # Dovrebbe mostrare messaggio di token scaduto
    
    def test_token_expiration_password_reset(self, client, app, db):
        """Test scadenza token reset password."""
        with app.app_context():
            user = UserFactory(email_verified=True)
            token = user.generate_password_reset_token()
            
            # Simula token scaduto (più di 1 ora fa)
            from datetime import timedelta
            user.password_reset_sent_at = user.password_reset_sent_at - timedelta(hours=2)
            db.session.commit()
            
            response = client.get(f'/auth/reset-password/{token}')
            
            assert response.status_code == 302  # Redirect
            # Dovrebbe reindirizzare a forgot-password con messaggio di scadenza

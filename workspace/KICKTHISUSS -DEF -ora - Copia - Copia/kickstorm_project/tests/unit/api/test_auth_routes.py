# tests/unit/api/test_auth_routes.py
import pytest
from flask import url_for
from tests.factories import UserFactory
from app.extensions import db


class TestAuthRoutes:
    """Test per le route di autenticazione."""

    def test_register_get(self, client):
        """Test GET pagina registrazione."""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'registration' in response.data.lower() or b'register' in response.data.lower()

    def test_register_post_success(self, client, app):
        """Test registrazione utente successo."""
        with app.app_context():
            response = client.post('/auth/register', data={
                'username': 'newuser',
                'email': 'newuser@test.com',
                'password': 'testpassword123',
                'confirm_password': 'testpassword123'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            
            # Verifica utente creato
            from app.models import User
            user = User.query.filter_by(email='newuser@test.com').first()
            assert user is not None
            assert user.username == 'newuser'

    def test_register_post_duplicate_email(self, client, app):
        """Test registrazione con email duplicata."""
        with app.app_context():
            # Crea utente esistente
            existing_user = UserFactory(email='existing@test.com')
            db.session.commit()
            
            response = client.post('/auth/register', data={
                'username': 'newuser',
                'email': 'existing@test.com',
                'password': 'testpassword123',
                'confirm_password': 'testpassword123'
            })
            
            assert response.status_code == 200
            # Il test dovrebbe rimanere sulla pagina di registrazione
            assert b'register' in response.data.lower() or b'registrat' in response.data.lower()

    def test_register_post_password_mismatch(self, client):
        """Test registrazione con password non corrispondenti."""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'testpassword123',
            'confirm_password': 'differentpassword'
        })
        
        assert response.status_code == 200
        assert b'password' in response.data.lower()

    def test_login_get(self, client):
        """Test GET pagina login."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower()

    def test_login_post_success(self, client, app):
        """Test login utente successo."""
        with app.app_context():
            # Crea utente
            user = UserFactory(email='test@example.com')
            user.set_password('testpassword123')
            db.session.commit()
            
            response = client.post('/auth/login', data={
                'email': 'test@example.com',
                'password': 'testpassword123'
            }, follow_redirects=True)
            
            assert response.status_code == 200

    def test_login_post_invalid_email(self, client):
        """Test login con email inesistente."""
        response = client.post('/auth/login', data={
            'email': 'nonexistent@test.com',
            'password': 'testpassword123'
        })
        
        assert response.status_code == 200
        # Dovrebbe rimanere sulla pagina di login
        assert b'login' in response.data.lower()

    def test_login_post_invalid_password(self, client, app):
        """Test login con password errata."""
        with app.app_context():
            user = UserFactory(email='test@example.com')
            user.set_password('correctpassword')
            db.session.commit()
            
            response = client.post('/auth/login', data={
                'email': 'test@example.com',
                'password': 'wrongpassword'
            })
            
            assert response.status_code == 200
            # Dovrebbe rimanere sulla pagina di login
            assert b'login' in response.data.lower()

    def test_logout(self, authenticated_client):
        """Test logout utente."""
        response = authenticated_client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200

    def test_protected_route_without_auth(self, client):
        """Test accesso route protetta senza autenticazione."""
        response = client.get('/users/profile/testuser', follow_redirects=True)
        assert response.status_code == 200
        # Dovrebbe essere reindirizzato al login
        assert b'login' in response.data.lower()
        assert b'login' in response.data.lower()

    def test_authenticated_user_redirect_from_auth_pages(self, authenticated_client):
        """Test redirect utente autenticato da pagine auth."""
        # Utente autenticato che prova ad accedere a login/register
        # dovrebbe essere reindirizzato
        response = authenticated_client.get('/auth/login', follow_redirects=True)
        assert response.status_code == 200
        
        response = authenticated_client.get('/auth/register', follow_redirects=True)
        assert response.status_code == 200

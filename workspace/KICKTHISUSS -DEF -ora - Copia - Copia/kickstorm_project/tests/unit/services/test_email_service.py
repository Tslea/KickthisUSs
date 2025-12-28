# tests/unit/services/test_email_service.py
"""
Test per il servizio email di KICKStorm
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import current_app
from flask_mail import Message

from app.email_service import (
    send_email, 
    send_verification_email, 
    send_password_reset_email, 
    send_welcome_email
)
from app.models import User
from tests.factories import UserFactory


class TestEmailService:
    """Test per il servizio email."""
    
    def test_send_email_with_valid_config(self, app):
        """Test invio email con configurazione valida."""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            
            with patch('app.email_service.Thread') as mock_thread:
                result = send_email(
                    subject="Test Email",
                    recipients=["test@example.com"],
                    text_body="Test body",
                    html_body="<p>Test HTML</p>"
                )
                
                assert result is True
                mock_thread.assert_called_once()
    
    def test_send_email_without_mail_server(self, app):
        """Test invio email senza server configurato."""
        with app.app_context():
            app.config['MAIL_SERVER'] = None
            
            result = send_email(
                subject="Test Email",
                recipients=["test@example.com"],
                text_body="Test body"
            )
            
            assert result is False
    
    def test_send_verification_email(self, app, db):
        """Test invio email di verifica."""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            app.config['SERVER_URL'] = 'http://localhost:5000'
            
            user = UserFactory()
            db.session.commit()
            
            with patch('app.email_service.send_email') as mock_send:
                mock_send.return_value = True
                result = send_verification_email(user)
                
                assert result is True
                assert user.email_verification_token is not None
                assert user.email_verification_sent_at is not None
                
                # Verifica chiamata a send_email
                mock_send.assert_called_once()
                args, kwargs = mock_send.call_args
                assert "Verifica il tuo account" in args[0]
                assert user.email in args[1]
    
    def test_send_password_reset_email(self, app, db):
        """Test invio email reset password."""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            app.config['SERVER_URL'] = 'http://localhost:5000'
            
            user = UserFactory()
            db.session.commit()
            
            with patch('app.email_service.send_email') as mock_send:
                mock_send.return_value = True
                result = send_password_reset_email(user)
                
                assert result is True
                assert user.password_reset_token is not None
                assert user.password_reset_sent_at is not None
                
                # Verifica chiamata a send_email
                mock_send.assert_called_once()
                args, kwargs = mock_send.call_args
                assert "Reset della password" in args[0]
                assert user.email in args[1]
    
    def test_send_welcome_email(self, app, db):
        """Test invio email di benvenuto."""
        with app.app_context():
            app.config['MAIL_SERVER'] = 'smtp.gmail.com'
            app.config['SERVER_URL'] = 'http://localhost:5000'
            
            user = UserFactory()
            db.session.commit()
            
            with patch('app.email_service.send_email') as mock_send:
                mock_send.return_value = True
                result = send_welcome_email(user)
                
                assert result is True
                
                # Verifica chiamata a send_email
                mock_send.assert_called_once()
                args, kwargs = mock_send.call_args
                assert "Benvenuto su KICKStorm!" in args[0]
                assert user.email in args[1]


class TestEmailTemplates:
    """Test per i template email."""
    
    def test_verification_email_template_render(self, app, db):
        """Test rendering template verifica email."""
        with app.app_context():
            user = UserFactory()
            token = "test_token_123"
            
            # Test del rendering del template
            from flask import render_template
            html_content = render_template(
                'emails/verify_email.html',
                user=user,
                token=token,
                server_url='http://localhost:5000'
            )
            
            assert user.username in html_content
            assert token in html_content
            assert "Verifica il tuo account" in html_content
            assert "KICKStorm" in html_content
    
    def test_reset_password_template_render(self, app, db):
        """Test rendering template reset password."""
        with app.app_context():
            user = UserFactory()
            token = "reset_token_456"
            
            from flask import render_template
            html_content = render_template(
                'emails/reset_password.html',
                user=user,
                token=token,
                server_url='http://localhost:5000'
            )
            
            assert user.username in html_content
            assert token in html_content
            assert "Reset della Password" in html_content
            assert "1 ora" in html_content  # Validità del token
    
    def test_welcome_email_template_render(self, app, db):
        """Test rendering template benvenuto."""
        with app.app_context():
            user = UserFactory()
            
            from flask import render_template
            html_content = render_template(
                'emails/welcome.html',
                user=user,
                server_url='http://localhost:5000'
            )
            
            assert user.username in html_content
            assert "Benvenuto su KICKStorm!" in html_content
            assert "projects" in html_content  # Link ai progetti

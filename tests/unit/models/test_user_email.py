# tests/unit/models/test_user_email.py
"""
Test per i metodi email del modello User
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.models import User
from tests.factories import UserFactory


class TestUserEmailMethods:
    """Test per i metodi di gestione email dell'utente."""
    
    def test_generate_email_verification_token(self, app, db):
        """Test generazione token verifica email."""
        with app.app_context():
            user = UserFactory()
            db.session.commit()
            
            token = user.generate_email_verification_token()
            
            assert token is not None
            assert len(token) > 20  # Token abbastanza lungo
            assert user.email_verification_token == token
            assert user.email_verification_sent_at is not None
            assert isinstance(user.email_verification_sent_at, datetime)
    
    def test_verify_email(self, app, db):
        """Test verifica email."""
        with app.app_context():
            user = UserFactory(email_verified=False)
            user.email_verification_token = "test_token"
            user.email_verification_sent_at = datetime.now(timezone.utc)
            db.session.commit()
            
            user.verify_email()
            
            assert user.email_verified is True
            assert user.email_verification_token is None
            assert user.email_verification_sent_at is None
    
    def test_generate_password_reset_token(self, app, db):
        """Test generazione token reset password."""
        with app.app_context():
            user = UserFactory()
            db.session.commit()
            
            token = user.generate_password_reset_token()
            
            assert token is not None
            assert len(token) > 20  # Token abbastanza lungo
            assert user.password_reset_token == token
            assert user.password_reset_sent_at is not None
            assert isinstance(user.password_reset_sent_at, datetime)
    
    def test_reset_password(self, app, db):
        """Test reset password."""
        with app.app_context():
            user = UserFactory()
            user.password_reset_token = "reset_token"
            user.password_reset_sent_at = datetime.now(timezone.utc)
            old_password_hash = user.password_hash
            db.session.commit()
            
            new_password = "new_secure_password123"
            user.reset_password(new_password)
            
            assert user.password_hash != old_password_hash
            assert user.check_password(new_password)
            assert user.password_reset_token is None
            assert user.password_reset_sent_at is None
    
    def test_token_uniqueness(self, app, db):
        """Test che i token generati siano unici."""
        with app.app_context():
            user1 = UserFactory()
            user2 = UserFactory()
            db.session.commit()
            
            token1 = user1.generate_email_verification_token()
            token2 = user2.generate_email_verification_token()
            
            assert token1 != token2
            
            reset_token1 = user1.generate_password_reset_token()
            reset_token2 = user2.generate_password_reset_token()
            
            assert reset_token1 != reset_token2
    
    def test_email_verified_default_value(self, app, db):
        """Test che email_verified sia False di default."""
        with app.app_context():
            user = UserFactory()
            db.session.commit()
            
            # Il factory potrebbe impostare email_verified, quindi testiamo direttamente
            new_user = User(
                username="testuser_default",
                email="test_default@example.com"
            )
            new_user.set_password("password123")
            db.session.add(new_user)
            db.session.commit()
            
            assert new_user.email_verified is False or new_user.email_verified is None
    
    def test_token_fields_nullable(self, app, db):
        """Test che i campi token siano nullable."""
        with app.app_context():
            user = UserFactory()
            user.email_verification_token = None
            user.email_verification_sent_at = None
            user.password_reset_token = None
            user.password_reset_sent_at = None
            
            db.session.commit()
            
            # Non dovrebbe lanciare errori
            assert user.email_verification_token is None
            assert user.password_reset_token is None

"""
Test suite per l'autenticazione a due fattori (2FA)
Tests per: User model 2FA methods, setup, verification, backup codes
"""

import unittest
from datetime import datetime, timezone
import json
import pyotp

from app import create_app
from app.extensions import db
from app.models import User


class TestTwoFactorAuthentication(unittest.TestCase):
    """Test per l'autenticazione a due fattori"""

    def setUp(self):
        """Setup per ogni test"""
        test_config = {
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test-secret-key'
        }
        self.app = create_app(test_config)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Crea le tabelle
        db.create_all()
        
        # Crea un utente di test
        self.user = User(
            username='testuser_2fa',
            email='test2fa@example.com'
        )
        self.user.set_password('testpassword')
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        """Cleanup dopo ogni test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_2fa_default_values(self):
        """Test che i valori di default 2FA siano corretti"""
        self.assertFalse(self.user.two_factor_enabled)
        self.assertIsNone(self.user.totp_secret)
        self.assertIsNone(self.user.backup_codes)

    def test_generate_totp_secret(self):
        """Test generazione secret TOTP"""
        secret = self.user.generate_totp_secret()
        
        self.assertIsNotNone(secret)
        self.assertEqual(len(secret), 32)  # Base32 secret standard length
        self.assertEqual(self.user.totp_secret, secret)

    def test_get_totp_uri(self):
        """Test generazione URI per QR code"""
        # Senza secret dovrebbe restituire None
        self.assertIsNone(self.user.get_totp_uri())
        
        # Con secret dovrebbe generare URI corretto
        self.user.generate_totp_secret()
        uri = self.user.get_totp_uri()
        
        self.assertIsNotNone(uri)
        self.assertIn('otpauth://totp/KickThisUss', uri)
        # L'email viene codificata in URL, quindi cerchiamo la versione codificata
        self.assertIn('test2fa%40example.com', uri)  # %40 è la codifica URL di @
        self.assertIn(self.user.totp_secret, uri)

    def test_verify_totp(self):
        """Test verifica token TOTP"""
        # Senza secret dovrebbe fallire
        self.assertFalse(self.user.verify_totp('123456'))
        
        # Con secret dovrebbe funzionare
        self.user.generate_totp_secret()
        
        # Genera un token valido
        totp = pyotp.TOTP(self.user.totp_secret)
        valid_token = totp.now()
        
        self.assertTrue(self.user.verify_totp(valid_token))
        self.assertFalse(self.user.verify_totp('000000'))  # Token invalido

    def test_generate_backup_codes(self):
        """Test generazione codici di backup"""
        codes = self.user.generate_backup_codes()
        
        self.assertEqual(len(codes), 10)  # Dovrebbe generare 10 codici
        self.assertIsNotNone(self.user.backup_codes)
        
        # Verifica che tutti i codici siano diversi
        self.assertEqual(len(set(codes)), 10)
        
        # Verifica che ogni codice sia di 8 caratteri (4 byte hex = 8 char)
        for code in codes:
            self.assertEqual(len(code), 8)
            # Verifica che sia esadecimale maiuscolo
            self.assertRegex(code, r'^[0-9A-F]{8}$')

    def test_get_backup_codes(self):
        """Test ottenimento codici di backup"""
        # Senza codici dovrebbe restituire lista vuota
        self.assertEqual(self.user.get_backup_codes(), [])
        
        # Con codici dovrebbe restituire la lista corretta
        generated_codes = self.user.generate_backup_codes()
        retrieved_codes = self.user.get_backup_codes()
        
        self.assertEqual(generated_codes, retrieved_codes)

    def test_use_backup_code(self):
        """Test utilizzo codici di backup"""
        codes = self.user.generate_backup_codes()
        original_count = len(codes)
        first_code = codes[0]
        
        # Usa un codice valido
        self.assertTrue(self.user.use_backup_code(first_code))
        
        # Verifica che il codice sia stato rimosso
        remaining_codes = self.user.get_backup_codes()
        self.assertEqual(len(remaining_codes), original_count - 1)
        self.assertNotIn(first_code, remaining_codes)
        
        # Prova a usare lo stesso codice di nuovo (dovrebbe fallire)
        self.assertFalse(self.user.use_backup_code(first_code))
        
        # Prova a usare un codice inesistente
        self.assertFalse(self.user.use_backup_code('INVALID1'))

    def test_enable_two_factor(self):
        """Test abilitazione 2FA"""
        self.assertFalse(self.user.two_factor_enabled)
        
        self.user.enable_two_factor()
        self.assertTrue(self.user.two_factor_enabled)

    def test_disable_two_factor(self):
        """Test disabilitazione 2FA"""
        # Setup iniziale
        self.user.generate_totp_secret()
        self.user.generate_backup_codes()
        self.user.enable_two_factor()
        
        # Verifica che tutto sia stato impostato
        self.assertTrue(self.user.two_factor_enabled)
        self.assertIsNotNone(self.user.totp_secret)
        self.assertIsNotNone(self.user.backup_codes)
        
        # Disabilita 2FA
        self.user.disable_two_factor()
        
        # Verifica che tutto sia stato pulito
        self.assertFalse(self.user.two_factor_enabled)
        self.assertIsNone(self.user.totp_secret)
        self.assertIsNone(self.user.backup_codes)

    def test_complete_2fa_workflow(self):
        """Test del workflow completo di setup 2FA"""
        # 1. Genera secret
        secret = self.user.generate_totp_secret()
        self.assertIsNotNone(secret)
        
        # 2. Verifica che si possa generare un QR code URI
        uri = self.user.get_totp_uri()
        self.assertIsNotNone(uri)
        
        # 3. Simula verifica del token durante setup
        totp = pyotp.TOTP(secret)
        token = totp.now()
        self.assertTrue(self.user.verify_totp(token))
        
        # 4. Genera codici di backup
        backup_codes = self.user.generate_backup_codes()
        self.assertEqual(len(backup_codes), 10)
        
        # 5. Abilita 2FA
        self.user.enable_two_factor()
        self.assertTrue(self.user.two_factor_enabled)
        
        # 6. Testa login con TOTP
        new_token = totp.now()
        self.assertTrue(self.user.verify_totp(new_token))
        
        # 7. Testa login con backup code
        first_backup = backup_codes[0]
        self.assertTrue(self.user.use_backup_code(first_backup))
        
        # 8. Verifica che il backup code sia stato rimosso
        self.assertEqual(len(self.user.get_backup_codes()), 9)


if __name__ == '__main__':
    unittest.main()

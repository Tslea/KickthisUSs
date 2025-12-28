#!/usr/bin/env python3
"""
Script di test per verificare la configurazione email Gmail SMTP
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Aggiungi il path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.email_service import send_email
from flask import current_app

def test_email_configuration():
    """Test della configurazione email"""
    
    print("🔧 Test Configurazione Email Gmail SMTP")
    print("=" * 50)
    
    # Crea l'app
    app = create_app()
    
    with app.app_context():
        # Verifica variabili di configurazione
        config_vars = [
            'MAIL_SERVER',
            'MAIL_PORT', 
            'MAIL_USERNAME',
            'MAIL_PASSWORD',
            'MAIL_DEFAULT_SENDER'
        ]
        
        print("📋 Verifica Configurazione:")
        missing_vars = []
        
        for var in config_vars:
            value = current_app.config.get(var)
            if value:
                if var == 'MAIL_PASSWORD':
                    print(f"✅ {var}: {'*' * len(str(value))}")
                else:
                    print(f"✅ {var}: {value}")
            else:
                print(f"❌ {var}: NON CONFIGURATO")
                missing_vars.append(var)
        
        if missing_vars:
            print(f"\n❌ ERRORE: Variabili mancanti: {', '.join(missing_vars)}")
            print("\n📝 Configura le variabili nel file .env:")
            print("MAIL_USERNAME=tua-email@gmail.com")
            print("MAIL_PASSWORD=tua-app-password-16-caratteri")
            print("MAIL_DEFAULT_SENDER=tua-email@gmail.com")
            return False
        
        print("\n✅ Tutte le configurazioni sono presenti!")
        
        # Test invio email (opzionale)
        test_email = input("\n📧 Vuoi testare l'invio di una email? (y/N): ").lower()
        
        if test_email == 'y':
            recipient = input("Inserisci email destinatario: ")
            if recipient:
                try:
                    print("📤 Invio email di test...")
                    success = send_email(
                        subject="Test Configurazione Gmail SMTP",
                        recipients=[recipient],
                        text_body="Questa è una email di test per verificare la configurazione Gmail SMTP di KICKStorm.",
                        html_body="""
                        <h2>✅ Test Email Funzionante!</h2>
                        <p>La configurazione Gmail SMTP di <strong>KICKStorm</strong> è stata configurata correttamente.</p>
                        <p>Ora puoi:</p>
                        <ul>
                            <li>Ricevere email di verifica account</li>
                            <li>Ricevere email di reset password</li>
                            <li>Ricevere notifiche di sistema</li>
                        </ul>
                        <hr>
                        <p><small>Team KICKStorm</small></p>
                        """
                    )
                    
                    if success:
                        print("✅ Email di test inviata con successo!")
                        print("📥 Controlla la tua casella email (anche spam)")
                    else:
                        print("❌ Errore nell'invio dell'email di test")
                        
                except Exception as e:
                    print(f"❌ Errore durante il test: {e}")
        
        return True

def show_gmail_setup_guide():
    """Mostra la guida per configurare Gmail"""
    
    print("\n📧 GUIDA CONFIGURAZIONE GMAIL:")
    print("=" * 50)
    print("1. Vai su https://myaccount.google.com/security")
    print("2. Attiva 'Verifica in 2 passaggi' (obbligatorio)")
    print("3. Vai su 'Password per le app'")
    print("4. Seleziona 'App: Mail' e 'Dispositivo: Computer Windows'")
    print("5. Copia la password generata (16 caratteri)")
    print("6. Inseriscila nel file .env come MAIL_PASSWORD")
    print("\n💡 IMPORTANTE: Usa la password per app, NON la tua password Gmail normale!")

if __name__ == "__main__":
    try:
        if not test_email_configuration():
            show_gmail_setup_guide()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrotto dall'utente")
    except Exception as e:
        print(f"\n❌ Errore durante il test: {e}")
        show_gmail_setup_guide()

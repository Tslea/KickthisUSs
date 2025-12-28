# app/email_service.py
"""
Servizio email per KICKStorm - configurazione Gmail SMTP
"""

from flask import current_app, render_template
from flask_mail import Message
from .extensions import mail
from threading import Thread
import os

def send_async_email(app, msg):
    """Invia email in background thread."""
    with app.app_context():
        try:
            mail.send(msg)
            current_app.logger.info(f"Email inviata con successo a {msg.recipients}")
        except Exception as e:
            current_app.logger.error(f"Errore invio email a {msg.recipients}: {e}")

def send_email(subject, recipients, text_body=None, html_body=None):
    """
    Invia email utilizzando Gmail SMTP.
    
    Args:
        subject: Oggetto dell'email
        recipients: Lista di destinatari
        text_body: Corpo testuale
        html_body: Corpo HTML
    """
    if not current_app.config.get('MAIL_SERVER'):
        current_app.logger.warning("MAIL_SERVER non configurato - email non inviata")
        return False
    
    if isinstance(recipients, str):
        recipients = [recipients]
    
    msg = Message(
        subject=f"[KICKStorm] {subject}",
        recipients=recipients,
        body=text_body,
        html=html_body
    )
    
    # Invia in background per non bloccare l'applicazione
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()
    
    return True

def send_verification_email(user):
    """Invia email di verifica account."""
    token = user.generate_email_verification_token()
    
    subject = "Verifica il tuo account"
    
    # Corpo testuale
    text_body = f"""
Ciao {user.username}!

Grazie per esserti registrato su KICKStorm. 
Per completare la registrazione, clicca sul link seguente per verificare il tuo indirizzo email:

{current_app.config.get('SERVER_URL', 'http://localhost:5000')}/auth/verify-email/{token}

Se non hai richiesto questa registrazione, ignora questa email.

Il team KICKStorm
"""
    
    # Corpo HTML (template da creare)
    html_body = render_template(
        'emails/verify_email.html',
        user=user,
        token=token,
        server_url=current_app.config.get('SERVER_URL', 'http://localhost:5000')
    )
    
    return send_email(subject, user.email, text_body, html_body)

def send_password_reset_email(user):
    """Invia email per reset password."""
    token = user.generate_password_reset_token()
    
    subject = "Reset della password"
    
    # Corpo testuale
    text_body = f"""
Ciao {user.username}!

Hai richiesto di reimpostare la password del tuo account KICKStorm.
Clicca sul link seguente per impostare una nuova password:

{current_app.config.get('SERVER_URL', 'http://localhost:5000')}/auth/reset-password/{token}

Se non hai richiesto questo reset, ignora questa email.
Il link sarà valido per 1 ora.

Il team KICKStorm
"""
    
    # Corpo HTML
    html_body = render_template(
        'emails/reset_password.html',
        user=user,
        token=token,
        server_url=current_app.config.get('SERVER_URL', 'http://localhost:5000')
    )
    
    return send_email(subject, user.email, text_body, html_body)

def send_welcome_email(user):
    """Invia email di benvenuto dopo verifica."""
    subject = "Benvenuto su KICKStorm!"
    
    text_body = f"""
Ciao {user.username}!

Il tuo account è stato verificato con successo! 🎉

Ora puoi accedere a tutte le funzionalità di KICKStorm:
- Creare e gestire progetti innovativi
- Collaborare con altri maker
- Utilizzare l'AI per ottimizzare i tuoi progetti
- Partecipare al sistema di equity

Inizia subito: {current_app.config.get('SERVER_URL', 'http://localhost:5000')}/projects

Buon making!
Il team KICKStorm
"""
    
    html_body = render_template(
        'emails/welcome.html',
        user=user,
        server_url=current_app.config.get('SERVER_URL', 'http://localhost:5000')
    )
    
    return send_email(subject, user.email, text_body, html_body)

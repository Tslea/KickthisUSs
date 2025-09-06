# app/email_middleware.py
"""
Middleware per gestire la verifica email degli utenti
"""

from flask import request, redirect, url_for, flash, current_app
from flask_login import current_user
from functools import wraps

def email_verification_required(f):
    """
    Decorator per richiede che l'utente abbia verificato l'email.
    Da usare su route che richiedono email verificata.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            # Se l'utente è loggato ma non ha verificato l'email
            if not current_user.email_verified:
                flash('Devi verificare la tua email prima di accedere a questa funzionalità. Controlla la tua casella di posta!', 'warning')
                return redirect(url_for('projects.home'))
        return f(*args, **kwargs)
    return decorated_function

def init_email_middleware(app):
    """Inizializza il middleware email per l'app."""
    
    @app.before_request
    def check_email_verification():
        """Verifica che l'utente abbia l'email verificata per certe azioni."""
        
        # Lista delle route che richiedono email verificata
        email_required_endpoints = [
            'projects.create_project',
            'tasks.add_task',
            'tasks.submit_solution',
            'api_projects.create_project',
            'wiki.create_wiki_page',
            'api_help.generate_mvp_guide',
            # Aggiungi altre route qui
        ]
        
        # Se l'utente è autenticato e sta cercando di accedere a funzioni protette
        if (current_user.is_authenticated and 
            request.endpoint in email_required_endpoints and 
            not getattr(current_user, 'email_verified', False)):
            
            flash('⚠️ Devi verificare la tua email per utilizzare questa funzionalità. Controlla la tua casella di posta!', 'warning')
            return redirect(url_for('projects.home'))
        
        return None  # Continua normalmente

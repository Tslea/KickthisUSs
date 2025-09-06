# app/decorators.py

from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user
from .models import Collaborator, Project

def email_verification_required(f):
    """
    Decoratore per richiedere che l'utente abbia verificato la sua email
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.email_verified:
            flash('Devi verificare la tua email prima di accedere a questa funzionalità.', 'warning')
            return redirect(url_for('auth.profile'))
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(project_id_arg, roles):
    """
    Un decoratore per verificare che l'utente corrente abbia uno dei ruoli specificati
    per un dato progetto.
    
    :param project_id_arg: Il nome dell'argomento nella route che contiene il project_id.
    :param roles: Una lista di stringhe di ruoli richiesti (es. ['creator', 'admin']).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            project_id = kwargs.get(project_id_arg)
            if not project_id:
                # Se non troviamo il project_id, è un errore di configurazione del server.
                abort(500, description="ID del progetto non trovato nella richiesta.")

            if not current_user.is_authenticated:
                # Se l'utente non è loggato, neghiamo l'accesso.
                abort(403)

            # Controlliamo se esiste una collaborazione per questo utente e progetto con il ruolo richiesto.
            collaboration = Collaborator.query.filter_by(
                project_id=project_id,
                user_id=current_user.id
            ).first()

            if not collaboration or collaboration.role not in roles:
                # Se non c'è collaborazione o il ruolo non è corretto, neghiamo l'accesso.
                abort(403, description="Non hai i permessi necessari per eseguire questa azione.")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

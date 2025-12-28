# app/decorators.py

from functools import wraps
from flask import abort, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from .models import Collaborator, Project

def email_verification_required(func):
    """
    Decoratore per richiedere che l'utente abbia verificato la sua email
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.email_verified:
            flash('Devi verificare la tua email prima di accedere a questa funzionalità.', 'warning')
            return redirect(url_for('auth.profile'))
        
        return func(*args, **kwargs)
    return decorated_function

def role_required(project_id_arg, roles):
    """
    Un decoratore per verificare che l'utente corrente abbia uno dei ruoli specificati
    per un dato progetto.
    
    :param project_id_arg: Il nome dell'argomento nella route che contiene il project_id.
    :param roles: Una lista di stringhe di ruoli richiesti (es. ['creator', 'admin']).
    """
    def decorator(func):
        @wraps(func)
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
            
            return func(*args, **kwargs)
        return decorated_function
    return decorator

def project_member_required(func):
    """
    Decoratore per Hub Agents: consente accesso solo a creatori e collaboratori del progetto.
    Il project_id può essere in kwargs o in request.json (per API POST).
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # Helper per capire se è una API call
        is_api_call = (
            request.path.startswith('/hub-agents/api/') or
            request.path.startswith('/hub-agents/load/') or
            request.path.startswith('/hub-agents/save/') or
            request.path.startswith('/hub-agents/generate/') or
            request.path.startswith('/hub-agents/chat/') or
            'api' in request.path or
            request.is_json or
            request.accept_mimetypes.accept_json
        )
        
        if not current_user.is_authenticated:
            if is_api_call:
                return jsonify({"error": "Devi essere autenticato per accedere a questa risorsa.", "content": ""}), 403
            abort(403, description="Devi essere autenticato per accedere a questa risorsa.")
        
        # Cerca project_id negli argomenti della route
        project_id = kwargs.get('project_id')
        
        # Se non lo trova, prova nel JSON body (per API POST)
        if not project_id and request.is_json:
            project_id = request.json.get('project_id')
        
        # Se non lo trova, prova nei query params (per GET)
        if not project_id:
            project_id = request.args.get('project_id')
        
        if not project_id:
            if is_api_call:
                return jsonify({"error": "ID del progetto non fornito.", "content": ""}), 400
            abort(400, description="ID del progetto non fornito.")
        
        # Verifica che l'utente sia creatore o collaboratore
        project = Project.query.get(project_id)
        if not project:
            if is_api_call:
                return jsonify({"error": "Progetto non trovato.", "content": ""}), 404
            abort(404, description="Progetto non trovato.")
        
        # Creatore ha sempre accesso
        if project.creator_id == current_user.id:
            return func(*args, **kwargs)
        
        # Controlla se è collaboratore
        collaboration = Collaborator.query.filter_by(
            project_id=project_id,
            user_id=current_user.id
        ).first()
        
        if not collaboration:
            if is_api_call:
                return jsonify({"error": "Non hai i permessi per accedere a questo progetto.", "content": ""}), 403
            abort(403, description="Non hai i permessi per accedere a questo progetto. Solo creatori e collaboratori possono usare Hub Agents.")
        
        return func(*args, **kwargs)
    return decorated_function

from flask import render_template, request, jsonify, redirect, url_for, current_app
from flask_login import current_user
from . import db
import traceback


def unauthorized_error(error):
    """
    Gestisce gli errori 401 Unauthorized.
    
    Risponde con JSON per le API requests, altrimenti reindirizza al login.
    """
    current_app.logger.warning(
        f"401 Unauthorized: {request.method} {request.path} "
        f"(User: {current_user.id if current_user.is_authenticated else 'Anonymous'}, "
        f"IP: {request.remote_addr})"
    )
    
    # Se la richiesta si aspetta JSON (tipico per le API), rispondi con JSON.
    # Questo previene il reindirizzamento alla pagina di login per le chiamate API
    # e impedisce l'errore "Unexpected token '<'" nel frontend.
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'error': 'Unauthorized', 
            'message': 'Autenticazione richiesta.',
            'status': 401
        }), 401
    
    # Altrimenti, per le normali richieste del browser, reindirizza alla pagina di login.
    return redirect(url_for('auth.login'))


def not_found_error(error):
    """
    Gestisce gli errori 404 Not Found.
    
    Risponde con JSON per le API requests, altrimenti mostra pagina 404 custom.
    """
    current_app.logger.info(
        f"404 Not Found: {request.method} {request.path} "
        f"(Referrer: {request.referrer}, IP: {request.remote_addr})"
    )
    
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'error': 'Not Found',
            'message': 'La risorsa richiesta non esiste.',
            'status': 404
        }), 404
    
    return render_template('errors/404.html'), 404


def internal_error(error):
    """
    Gestisce gli errori 500 Internal Server Error.
    
    Esegue rollback del database, logga l'errore completo con traceback,
    e risponde in modo appropriato (JSON o HTML).
    """
    # CRITICAL: Rollback database per prevenire dati corrotti
    try:
        db.session.rollback()
    except Exception as rollback_error:
        current_app.logger.error(f"Failed to rollback database: {rollback_error}")
    
    # Log completo dell'errore con traceback per debugging
    current_app.logger.error(
        f"500 Internal Server Error: {request.method} {request.path}\n"
        f"User: {current_user.id if current_user.is_authenticated else 'Anonymous'}\n"
        f"IP: {request.remote_addr}\n"
        f"User-Agent: {request.user_agent}\n"
        f"Error: {str(error)}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )
    
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'Si è verificato un errore interno. Il team è stato notificato.',
            'status': 500
        }), 500
    
    return render_template('errors/500.html'), 500


def forbidden_error(error):
    """
    Gestisce gli errori 403 Forbidden.
    
    Logga il tentativo di accesso non autorizzato e risponde appropriatamente.
    """
    current_app.logger.warning(
        f"403 Forbidden: {request.method} {request.path} "
        f"(User: {current_user.id if current_user.is_authenticated else 'Anonymous'}, "
        f"IP: {request.remote_addr}, "
        f"Referrer: {request.referrer})"
    )
    
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'error': 'Forbidden',
            'message': 'Non hai i permessi per accedere a questa risorsa.',
            'status': 403
        }), 403
    
    return render_template('errors/403.html'), 403


def rate_limit_error(error):
    """
    Gestisce gli errori 429 Too Many Requests (rate limiting).
    
    Risponde con informazioni sul retry-after time.
    """
    current_app.logger.warning(
        f"429 Too Many Requests: {request.method} {request.path} "
        f"(User: {current_user.id if current_user.is_authenticated else 'Anonymous'}, "
        f"IP: {request.remote_addr})"
    )
    
    # Get retry-after time from error if available
    retry_after = getattr(error, 'description', 'Rate limit exceeded. Please try again later.')
    
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            'error': 'Too Many Requests',
            'message': 'Hai superato il limite di richieste. Riprova più tardi.',
            'retry_after': retry_after,
            'status': 429
        }), 429
    
    # Per richieste HTML, reindirizza a pagina di errore generica o mostra messaggio
    return render_template('errors/429.html', retry_after=retry_after), 429


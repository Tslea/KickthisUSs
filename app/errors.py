from flask import render_template, request, jsonify, redirect, url_for
from flask_login import current_user
from . import db

def unauthorized_error(error):
    """Gestisce gli errori 401 Unauthorized."""
    # Se la richiesta si aspetta JSON (tipico per le API), rispondi con JSON.
    # Questo previene il reindirizzamento alla pagina di login per le chiamate API
    # e impedisce l'errore "Unexpected token '<'" nel frontend.
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({'error': 'Unauthorized', 'message': 'Autenticazione richiesta.'}), 401
    
    # Altrimenti, per le normali richieste del browser, reindirizza alla pagina di login.
    return redirect(url_for('auth.login'))


def not_found_error(error):
    """Gestisce gli errori 404 Not Found."""
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({'error': 'Not Found'}), 404
    return render_template('errors/404.html'), 404


def internal_error(error):
    """Gestisce gli errori 500 Internal Server Error."""
    db.session.rollback()
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({'error': 'Internal Server Error'}), 500
    return render_template('errors/500.html'), 500

def forbidden_error(error):
    """Gestisce gli errori 403 Forbidden."""
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({'error': 'Forbidden'}), 403
    return render_template('errors/403.html'), 403

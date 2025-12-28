# app/api_help.py

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from flask_wtf.csrf import validate_csrf

from .ai_services import get_ai_contextual_help

api_help_bp = Blueprint('api_help', __name__)

@api_help_bp.route('/api/help', methods=['POST'])
@login_required
def get_contextual_help():
    """
    Endpoint API per fornire aiuto contestuale tramite AI.
    Riceve un contesto e restituisce una guida personalizzata.
    """
    try:
        # Valida il token CSRF
        csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
        if csrf_token:
            try:
                validate_csrf(csrf_token)
            except Exception as e:
                current_app.logger.warning(f"Token CSRF invalido: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Token CSRF invalido'
                }), 400
        data = request.get_json()
        if not data or 'context' not in data:
            return jsonify({
                'success': False,
                'error': 'Parametro context richiesto'
            }), 400
        
        context = data['context']
        
        # Valida i contesti supportati
        supported_contexts = [
            'github_workflow',
            'hardware_submission', 
            'task_creation',
            'project_collaboration',
            'solution_submission'
        ]
        
        if context not in supported_contexts:
            return jsonify({
                'success': False,
                'error': f'Contesto non supportato. Contesti disponibili: {", ".join(supported_contexts)}'
            }), 400
        
        # Chiama il servizio AI per ottenere l'aiuto
        help_content = get_ai_contextual_help(context)
        
        if help_content:
            return jsonify({
                'success': True,
                'context': context,
                'help_content': help_content
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Servizio AI non disponibile. Riprova più tardi.'
            }), 503
            
    except Exception as e:
        current_app.logger.error(f"Errore API aiuto contestuale: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Errore interno del server'
        }), 500

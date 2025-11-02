# app/routes_webhooks.py
"""
Webhook endpoints per sincronizzazione bidirezionale con GitHub.
Riceve notifiche da GitHub quando gli issues vengono modificati.
"""

from flask import Blueprint, request, jsonify, current_app
import hmac
import hashlib
from datetime import datetime

from .extensions import db
from .models import Task, Project

webhooks_bp = Blueprint('webhooks', __name__, url_prefix='/webhooks')


def verify_github_signature(payload_body, signature_header, secret):
    """Verifica la firma del webhook GitHub"""
    if not signature_header:
        return False
    
    hash_algorithm, github_signature = signature_header.split('=')
    algorithm = hashlib.__dict__.get(hash_algorithm)
    encoded_secret = bytes(secret, 'utf-8')
    mac = hmac.new(encoded_secret, msg=payload_body, digestmod=algorithm)
    
    return hmac.compare_digest(mac.hexdigest(), github_signature)


@webhooks_bp.route('/github', methods=['POST'])
def github_webhook():
    """
    Riceve webhook da GitHub per sincronizzare modifiche agli issues.
    
    Configurazione webhook su GitHub:
    - Payload URL: https://tuodomain.com/webhooks/github
    - Content type: application/json
    - Events: Issues
    """
    # Verifica firma webhook (opzionale ma raccomandato)
    signature = request.headers.get('X-Hub-Signature-256')
    webhook_secret = current_app.config.get('GITHUB_WEBHOOK_SECRET')
    
    if webhook_secret and signature:
        if not verify_github_signature(request.data, signature, webhook_secret):
            current_app.logger.warning("Invalid webhook signature")
            return jsonify({'error': 'Invalid signature'}), 401
    
    # Ottieni payload
    payload = request.json
    event_type = request.headers.get('X-GitHub-Event')
    
    current_app.logger.info(f"Received GitHub webhook: {event_type}")
    
    # Gestisci solo eventi di tipo "issues"
    if event_type != 'issues':
        return jsonify({'message': 'Event type not handled'}), 200
    
    action = payload.get('action')
    issue = payload.get('issue', {})
    repository = payload.get('repository', {})
    
    issue_number = issue.get('number')
    repo_full_name = repository.get('full_name')
    issue_state = issue.get('state')  # 'open' or 'closed'
    
    current_app.logger.info(f"Issue #{issue_number} in {repo_full_name}: action={action}, state={issue_state}")
    
    try:
        # Trova il progetto con questo repository
        project = Project.query.filter_by(github_repo_name=repo_full_name).first()
        
        if not project:
            current_app.logger.warning(f"No project found for repository {repo_full_name}")
            return jsonify({'message': 'Repository not linked to any project'}), 200
        
        # Trova il task con questo issue number
        task = Task.query.filter_by(
            project_id=project.id,
            github_issue_number=issue_number
        ).first()
        
        if not task:
            current_app.logger.warning(f"No task found for issue #{issue_number}")
            return jsonify({'message': 'Issue not linked to any task'}), 200
        
        # Sincronizza lo stato
        if action == 'closed':
            if task.status != 'completed':
                task.status = 'completed'
                current_app.logger.info(f"Task {task.id} marked as completed (from GitHub)")
        elif action == 'reopened':
            if task.status == 'completed':
                task.status = 'in_progress'
                current_app.logger.info(f"Task {task.id} reopened (from GitHub)")
        elif action == 'edited':
            # Aggiorna titolo e descrizione se modificati
            new_title = issue.get('title')
            new_body = issue.get('body')
            
            if new_title and new_title != task.title:
                task.title = new_title
                current_app.logger.info(f"Task {task.id} title updated from GitHub")
            
            if new_body:
                # Rimuovi la firma KickThisUSS dal body se presente
                if '---' in new_body and 'Sincronizzato automaticamente da KickThisUSS' in new_body:
                    new_body = new_body.split('---')[0].strip()
                
                if new_body != task.description:
                    task.description = new_body
                    current_app.logger.info(f"Task {task.id} description updated from GitHub")
        
        # Aggiorna timestamp sincronizzazione
        task.github_synced_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Task {task.id} synchronized'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing webhook: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@webhooks_bp.route('/github/test', methods=['GET'])
def test_webhook():
    """Endpoint per testare che il webhook sia raggiungibile"""
    return jsonify({
        'status': 'ok',
        'message': 'Webhook endpoint is reachable'
    }), 200

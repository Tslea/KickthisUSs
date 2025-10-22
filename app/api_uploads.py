# app/api_uploads.py
import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .extensions import limiter
from .file_validation import validate_file_upload, get_safe_filename, FileValidationError

# NUOVO: Import GitHub sync service (opzionale)
try:
    from .services import GitHubSyncService
    GITHUB_SYNC_AVAILABLE = True
except ImportError:
    GITHUB_SYNC_AVAILABLE = False
    GitHubSyncService = None

api_uploads_bp = Blueprint('api_uploads', __name__)

# Estensioni di file consentite per le immagini (backward compatibility)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# MIME types consentiti per immagini
ALLOWED_IMAGE_MIME_TYPES = {
    'image/png',
    'image/jpeg', 
    'image/gif',
    'image/webp'
}

def allowed_file(filename):
    """Verifica se il file ha un'estensione consentita (legacy function)."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_unique_filename(filename):
    """Genera un nome di file univoco per evitare sovrascritture."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    random_uuid = uuid.uuid4().hex
    return f"{random_uuid}.{ext}" if ext else random_uuid

@api_uploads_bp.route('/upload-image', methods=['POST'])
@login_required
@limiter.limit("10 per hour")  # Strict rate limit for file uploads
def upload_image():
    """
    Endpoint API per caricare un'immagine con validazione avanzata.
    Valida MIME type reale del file, non solo l'estensione.
    """
    # Verifica se esiste una directory uploads, altrimenti la crea
    upload_folder = os.path.join(current_app.static_folder, 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Nessun file caricato'
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Nessun file selezionato'
        }), 400
    
    try:
        # Advanced validation with MIME type checking
        # Note: Will use config.py ALLOWED_MIME_TYPES, or fallback to ALLOWED_IMAGE_MIME_TYPES
        validation_result = validate_file_upload(
            file,
            check_mime=True,  # Validate real MIME type
            check_size=True   # Validate file size
        )
        
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'error': '; '.join(validation_result['errors'])
            }), 400
        
        # Additional check: ensure it's an image
        if validation_result['mime_type'] not in ALLOWED_IMAGE_MIME_TYPES:
            return jsonify({
                'success': False,
                'error': f"Solo immagini sono consentite. Tipo rilevato: {validation_result['mime_type']}"
            }), 400
        
        # Generate safe filename
        unique_filename = get_unique_filename(file.filename)
        file_path = os.path.join(upload_folder, unique_filename)
        
        # Save file LOCALLY (sempre, indipendentemente da GitHub)
        file.save(file_path)
        
        # Log upload for security audit
        current_app.logger.info(
            f"File uploaded by user {current_user.id}: {unique_filename} "
            f"(MIME: {validation_result['mime_type']}, Size: {validation_result['size']} bytes)"
        )
        
        # NUOVO: Opzionalmente sincronizza con GitHub (NON bloccante)
        # Se project_id è fornito e GitHub è abilitato GLOBALMENTE
        github_synced = False
        project_id = request.form.get('project_id')  # Opzionale
        if GITHUB_SYNC_AVAILABLE and project_id:
            try:
                from .models import Project
                project = Project.query.get(int(project_id))
                if project:  # Sync automatico se GitHub enabled globalmente
                    sync_service = GitHubSyncService()
                    if sync_service.is_enabled():
                        # Leggi il file appena salvato
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        # Sincronizza con GitHub (se fallisce, non è critico)
                        github_synced = sync_service.sync_file(
                            project=project,
                            file_path=f"images/{unique_filename}",
                            content=file_content,
                            commit_message=f"Upload image: {unique_filename}"
                        )
                        if github_synced:
                            current_app.logger.info(f"File synced to GitHub for project {project_id}")
            except Exception as e:
                # Log ma NON fallire - il file locale è salvato
                current_app.logger.warning(f"GitHub sync failed (non-critical): {e}")
        
        # Restituisci l'URL dell'immagine
        relative_path = f"/static/uploads/{unique_filename}"
        
        return jsonify({
            'success': True,
            'file': {
                'url': relative_path,
                'filename': unique_filename,
                'mime_type': validation_result['mime_type'],
                'size': validation_result['size'],
                'github_synced': github_synced  # NUOVO: indica se sincronizzato con GitHub
            }
        }), 200
        
    except FileValidationError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error during file upload: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Errore interno durante il caricamento del file'
        }), 500


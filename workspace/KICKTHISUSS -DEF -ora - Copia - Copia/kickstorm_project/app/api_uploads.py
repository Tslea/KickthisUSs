# app/api_uploads.py
import mimetypes
import os
import uuid
import json
import shutil
import tempfile
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app, abort, send_file
from flask_login import login_required, current_user
from itsdangerous import BadSignature, SignatureExpired
from .extensions import limiter, db
from .file_validation import validate_file_upload, get_safe_filename, FileValidationError
from .models import Project, Collaborator, Task, Solution
from .services.zip_processor import ZipProcessor, ZipProcessorError
from .workspace_utils import (
    ensure_project_workspace,
    session_dir as ws_session_dir,
    load_session_metadata,
    save_session_metadata,
    default_metadata,
    list_session_metadata,
    load_history_entries,
    list_repo_files,
    generate_file_token,
    verify_file_token,
    get_repo_file_path,
    sanitize_workspace_path
)
from .services.workspace_sync_service import WorkspaceSyncService
from .services.notification_service import NotificationService

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


def _get_project_with_access(project_id: int) -> Project:
    project = Project.query.get_or_404(project_id)
    if project.creator_id == current_user.id:
        return project
    collaborator = Collaborator.query.filter_by(
        project_id=project.id,
        user_id=current_user.id
    ).first()
    if collaborator:
        return project
    abort(403, description="Non hai i permessi per gestire i file di questo progetto.")


def _update_file_metadata(metadata: dict, relative_path: str, file_size: int, status: str = 'pending'):
    files = metadata.setdefault('files', [])
    existing = next((item for item in files if item['path'] == relative_path), None)
    if not existing:
        existing = {
            'path': relative_path,
            'size': file_size,
            'status': status,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        files.append(existing)
    else:
        existing['size'] = file_size
        existing['status'] = status
        existing['updated_at'] = datetime.now(timezone.utc).isoformat()
    metadata['file_count'] = len(files)
    metadata['total_size'] = sum(item.get('size', 0) for item in files)
    metadata['updated_at'] = datetime.now(timezone.utc).isoformat()


@api_uploads_bp.route('/projects/<int:project_id>/upload-zip', methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def upload_project_zip(project_id: int):
    """Upload completo di un archivio ZIP per un progetto."""
    project = _get_project_with_access(project_id)

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nessun archivio ZIP caricato.'}), 400

    zip_file = request.files['file']
    if not zip_file.filename:
        return jsonify({'success': False, 'error': 'Il file ZIP deve avere un nome valido.'}), 400

    print(f"[ZIP UPLOAD] Starting ZIP extraction for project {project.id}")
    current_app.logger.info("Starting ZIP extraction for project %s", project.id)
    
    processor = ZipProcessor()
    try:
        current_app.logger.debug("Calling processor.extract_zip...")
        extracted_files = processor.extract_zip(zip_file)
        print(f"[ZIP UPLOAD] ZIP extraction completed: {len(extracted_files)} files")
        current_app.logger.info("ZIP extraction completed: %d files", len(extracted_files))
    except ZipProcessorError as exc:
        current_app.logger.error("ZIP extraction failed: %s", exc)
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        current_app.logger.error("Unexpected error during ZIP extraction: %s", exc, exc_info=True)
        return jsonify({'success': False, 'error': f'Errore inaspettato: {str(exc)}'}), 500

    session_id = uuid.uuid4().hex
    session_directory = ws_session_dir(project.id, session_id)
    
    current_app.logger.debug("Session directory: %s", session_directory)

    # Copia l'intera struttura estratta nella cartella sessione
    if processor.temp_dir:
        current_app.logger.debug("Copying extracted files to session directory...")
        try:
            shutil.copytree(processor.temp_dir, session_directory, dirs_exist_ok=True)
            current_app.logger.debug("Files copied successfully")
            shutil.rmtree(processor.temp_dir, ignore_errors=True)
        except Exception as copy_error:
            current_app.logger.error("Error copying files: %s", copy_error, exc_info=True)
            return jsonify({'success': False, 'error': f'Errore copia file: {str(copy_error)}'}), 500

    metadata = default_metadata(session_id, project.id, upload_type='zip')
    metadata['initiated_by'] = current_user.id
    total_size = 0
    for file_info in extracted_files:
        try:
            relative_path = sanitize_workspace_path(file_info['path'])
        except ValueError:
            continue
        file_size = file_info['size']
        total_size += file_size
        _update_file_metadata(metadata, relative_path, file_size)

    metadata['status'] = 'extracted'
    metadata['file_count'] = len(extracted_files)
    metadata['total_size'] = total_size
    save_session_metadata(session_directory, metadata)
    
    # Forza flush per assicurarsi che il file sia scritto su disco (Windows safe)
    metadata_file = os.path.join(session_directory, 'metadata.json')
    if os.path.exists(metadata_file):
        try:
            # Su Windows, fsync richiede il file aperto in modalità write
            with open(metadata_file, 'r+') as f:
                f.flush()
                os.fsync(f.fileno())
            current_app.logger.debug("Metadata file flushed successfully")
        except (OSError, AttributeError) as e:
            current_app.logger.warning("Could not fsync metadata file: %s", e)

    print(f"[ZIP UPLOAD] ZIP upload completed - project: {project.id}, files: {len(extracted_files)}, session: {session_id}")
    current_app.logger.info("ZIP upload completed - project: %s, files: %s, session: %s, directory: %s", 
                           project.id, len(extracted_files), session_id, session_directory)
    
    # Verifica che il file sia leggibile
    try:
        from app.workspace_utils import load_session_metadata
        verify_metadata = load_session_metadata(session_directory)
        if verify_metadata:
            print(f"[ZIP UPLOAD] Session metadata verified - status: {verify_metadata.get('status')}, session_id: {verify_metadata.get('session_id')}")
            current_app.logger.debug("Session metadata verified - status: %s", verify_metadata.get('status'))
        else:
            print(f"[ZIP UPLOAD] CRITICAL: Session metadata not readable after save!")
            current_app.logger.error("CRITICAL: Session metadata not readable after save!")
    except Exception as e:
        print(f"[ZIP UPLOAD] Error verifying metadata: {e}")
        current_app.logger.error("Error verifying metadata: %s", e)

    # Smart Sync: Sincronizza workspace con GitHub (SINCRONO con git commands o ASINCRONO con Celery fallback)
    github_sync_result = None
    if GITHUB_SYNC_AVAILABLE and project.github_repo_name:
        try:
            current_app.logger.info("Starting workspace sync for project %s", project.id)
            
            # Prova sync sincrono con git commands (più veloce)
            # Se git non disponibile o fallisce, usa Celery come fallback
            try:
                from .services.git_sync_service import GitSyncService
                git_sync = GitSyncService()
                
                if git_sync.is_enabled():
                    # Sync sincrono con git (veloce, non blocca troppo)
                    current_app.logger.info("Using git sync (synchronous) for project %s", project.id)
                    metadata['status'] = 'syncing'
                    save_session_metadata(session_directory, metadata)
                    
                    sync_result = git_sync.sync_workspace_from_directory(
                        project, session_directory, current_user.id
                    )
                    
                    if sync_result.get('status') == 'success':
                        metadata['status'] = 'completed'
                        metadata['sync_finished_at'] = datetime.now(timezone.utc).isoformat()
                        metadata['sync_method'] = 'git'
                        save_session_metadata(session_directory, metadata)
                        
                        github_sync_result = {
                            'success': True,
                            'async': False,
                            'method': 'git',
                            'message': f"✅ Sync completato: {sync_result.get('files_synced', 0)} file caricati",
                            'files_synced': sync_result.get('files_synced', 0),
                            'commit_url': sync_result.get('commit_url')
                        }
                    else:
                        # Git sync fallito, fallback a Celery
                        raise Exception(f"Git sync failed: {sync_result.get('message')}")
                else:
                    raise Exception("Git sync not available")
                    
            except Exception as git_exc:
                # Fallback a Celery per sync asincrono
                current_app.logger.info("Git sync not available, using Celery async sync: %s", git_exc)
                
                try:
                    from tasks.github_tasks import sync_workspace_session
                    task = sync_workspace_session.delay(project.id, session_id, current_user.id)
                    
                    github_sync_result = {
                        'success': True,
                        'async': True,
                        'task_id': task.id,
                        'method': 'celery',
                        'message': "⏳ Sync avviato in background (Celery)..."
                    }
                    
                    metadata['status'] = 'syncing'
                    metadata['sync_task_id'] = task.id
                    save_session_metadata(session_directory, metadata)
                except Exception as celery_exc:
                    current_app.logger.error("Both git sync and Celery failed: %s", celery_exc, exc_info=True)
                    github_sync_result = {
                        'success': False,
                        'error': str(celery_exc),
                        'message': f"⚠️ Errore avvio sync: {str(celery_exc)}"
                    }
            
        except Exception as sync_exc:
            current_app.logger.error("Failed to start sync: %s", sync_exc, exc_info=True)
            github_sync_result = {
                'success': False,
                'error': str(sync_exc),
                'message': f"⚠️ Errore avvio sync: {str(sync_exc)}"
            }
    elif not GITHUB_SYNC_AVAILABLE:
        current_app.logger.debug("GitHub sync not available (GitHubSyncService not imported)")
    elif not project.github_repo_name:
        current_app.logger.debug("Project %s has no GitHub repository configured", project.id)

    response_data = {
        'success': True,
        'session_id': session_id,
        'file_count': len(extracted_files),
        'total_size': total_size,
        'workspace': {
            'incoming_dir': session_directory,
            'metadata': metadata
        }
    }
    
    if github_sync_result:
        response_data['github_sync'] = github_sync_result
    
    return jsonify(response_data), 200


@api_uploads_bp.route('/projects/<int:project_id>/files', methods=['POST'])
@login_required
@limiter.limit("30 per hour")
def upload_project_file(project_id: int):
    """Upload singolo file (supporto chunk opzionale)."""
    project = _get_project_with_access(project_id)

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nessun file caricato.'}), 400

    relative_path_param = request.form.get('relative_path') or request.form.get('path')
    try:
        relative_path = sanitize_workspace_path(relative_path_param)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    session_id = request.form.get('session_id') or uuid.uuid4().hex
    session_directory = ws_session_dir(project.id, session_id)

    destination_path = os.path.join(session_directory, relative_path)
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    chunk_index = request.form.get('chunk_index', type=int)
    total_chunks = request.form.get('total_chunks', type=int)

    uploaded_file = request.files['file']
    if chunk_index is None and total_chunks is None:
        # Validazione completa per upload singoli
        try:
            max_file_bytes = current_app.config.get('PROJECT_WORKSPACE_MAX_FILE_BYTES')
            validation_result = validate_file_upload(uploaded_file, max_size=max_file_bytes)
            if not validation_result['valid']:
                error_text = '; '.join(validation_result['errors'])
                lowered = error_text.lower()
                if 'unexpected error during file validation' in lowered or 'magic' in lowered:
                    current_app.logger.warning("File validation fallback per upload singolo: %s", error_text)
                else:
                    return jsonify({'success': False, 'error': error_text}), 400
        except Exception as exc:
            current_app.logger.warning("File validation fallback per upload singolo: %s", exc)
        finally:
            uploaded_file.seek(0)

    mode = 'ab' if chunk_index is not None and chunk_index > 0 else 'wb'
    with open(destination_path, mode) as dest:
        shutil.copyfileobj(uploaded_file.stream, dest)

    file_size = os.path.getsize(destination_path)
    metadata = load_session_metadata(session_directory) or default_metadata(session_id, project.id, upload_type='manual')
    metadata.setdefault('initiated_by', current_user.id)

    file_status = 'pending'
    if total_chunks is None or (chunk_index is not None and total_chunks and chunk_index + 1 == total_chunks):
        file_status = 'complete'

    _update_file_metadata(metadata, relative_path, file_size, status=file_status)
    metadata['status'] = 'in_progress'
    save_session_metadata(session_directory, metadata)

    return jsonify({
        'success': True,
        'session_id': session_id,
        'path': relative_path,
        'size': file_size,
        'chunk_index': chunk_index,
        'total_chunks': total_chunks
    }), 200


@api_uploads_bp.route('/projects/<int:project_id>/finalize-upload', methods=['POST'])
@login_required
def finalize_upload_session(project_id: int):
    """Segna una sessione di upload come pronta per la sincronizzazione."""
    project = _get_project_with_access(project_id)
    session_id = request.json.get('session_id') if request.is_json else request.form.get('session_id')
    if not session_id:
        return jsonify({'success': False, 'error': 'session_id mancante.'}), 400

    session_directory = ws_session_dir(project.id, session_id)
    metadata = load_session_metadata(session_directory)
    if not metadata:
        return jsonify({'success': False, 'error': 'Sessione non trovata.'}), 404

    metadata['status'] = 'ready'
    metadata['finalized_at'] = datetime.now(timezone.utc).isoformat()
    save_session_metadata(session_directory, metadata)

    current_app.logger.info("Sessione upload pronta per sync (project=%s, session=%s)", project.id, session_id)

    NotificationService.notify_workspace_upload_ready(project, metadata, current_user.id)
    db.session.commit()

    # Avvia sync (git sincrono o Celery asincrono come fallback)
    try:
        # Prova git sync sincrono prima
        try:
            from .services.git_sync_service import GitSyncService
            git_sync = GitSyncService()
            
            if git_sync.is_enabled():
                current_app.logger.info("Using git sync (synchronous) for session %s", session_id)
                metadata['status'] = 'syncing'
                save_session_metadata(session_directory, metadata)
                
                sync_result = git_sync.sync_workspace_from_directory(
                    project, session_directory, current_user.id
                )
                
                if sync_result.get('status') == 'success':
                    metadata['status'] = 'completed'
                    metadata['sync_finished_at'] = datetime.now(timezone.utc).isoformat()
                    metadata['sync_method'] = 'git'
                    save_session_metadata(session_directory, metadata)
                    
                    return jsonify({
                        'success': True, 
                        'session_id': session_id, 
                        'status': 'completed',
                        'method': 'git',
                        'message': f'Sincronizzazione completata: {sync_result.get("files_synced", 0)} file',
                        'files_synced': sync_result.get('files_synced', 0),
                        'commit_url': sync_result.get('commit_url')
                    }), 200
                else:
                    raise Exception(f"Git sync failed: {sync_result.get('message')}")
            else:
                raise Exception("Git sync not available")
        except Exception as git_exc:
            # Fallback a Celery
            current_app.logger.info("Git sync not available, using Celery: %s", git_exc)
            from tasks.github_tasks import sync_workspace_session
            task = sync_workspace_session.delay(project.id, session_id, current_user.id)
            
            metadata['status'] = 'syncing'
            metadata['sync_task_id'] = task.id
            save_session_metadata(session_directory, metadata)
            
            current_app.logger.info("Async sync scheduled for session %s (task %s)", session_id, task.id)
            
            return jsonify({
                'success': True, 
                'session_id': session_id, 
                'status': 'syncing',
                'method': 'celery',
                'message': 'Sincronizzazione avviata in background (Celery)'
            }), 200
        
    except Exception as exc:
        current_app.logger.error("Failed to start sync: %s", exc)
        metadata['status'] = 'error'
        metadata['error'] = str(exc)
        save_session_metadata(session_directory, metadata)
        return jsonify({'success': False, 'session_id': session_id, 'status': 'error', 'error': str(exc)}), 500

    return jsonify({'success': True, 'session_id': session_id, 'status': final_metadata['status'], 'metadata': final_metadata}), 200


@api_uploads_bp.route('/projects/<int:project_id>/sessions/<string:session_id>', methods=['DELETE'])
@login_required
@limiter.limit("15 per hour")
def delete_upload_session(project_id: int, session_id: str):
    """Permette al creatore/collaboratore di annullare una sessione di upload."""
    project = _get_project_with_access(project_id)
    incoming_root = os.path.join(ensure_project_workspace(project.id), 'incoming')
    session_directory = os.path.join(incoming_root, session_id)

    if not os.path.isdir(session_directory):
        return jsonify({'success': False, 'error': 'Sessione non trovata.'}), 404

    metadata = load_session_metadata(session_directory)
    protected_statuses = {'completed', 'syncing'}
    if metadata and metadata.get('status') in protected_statuses:
        return jsonify({'success': False, 'error': 'La sessione è già sincronizzata e non può essere rimossa.'}), 400

    shutil.rmtree(session_directory, ignore_errors=True)
    current_app.logger.info("Sessione workspace eliminata (project=%s, session=%s)", project.id, session_id)
    return jsonify({'success': True, 'session_id': session_id}), 200


@api_uploads_bp.route('/projects/<int:project_id>/sync-status', methods=['GET'])
@login_required
def get_sync_status(project_id: int):
    project = _get_project_with_access(project_id)
    session_id = request.args.get('session_id')

    repo_info = None
    if project.repository:
        repo_info = {
            'provider': project.repository.provider,
            'repo_name': project.repository.repo_name,
            'status': project.repository.status,
            'last_sync_at': project.repository.last_sync_at.isoformat() if project.repository.last_sync_at else None
        }

    if session_id:
        session_directory = ws_session_dir(project.id, session_id)
        metadata = load_session_metadata(session_directory)
        if not metadata:
            return jsonify({'success': False, 'error': 'Sessione non trovata.'}), 404
        return jsonify({'success': True, 'session_id': session_id, 'metadata': metadata, 'repository': repo_info}), 200

    history = load_history_entries(project.id, limit=5)
    sessions = list_session_metadata(project.id, limit=10)  # Aumentato limite per essere sicuri
    print(f"[SYNC STATUS] Sync status for project {project.id}: {len(sessions)} sessions found")
    if sessions:
        for s in sessions:
            print(f"  - Session: {s.get('session_id', 'unknown')[:8]}..., status: {s.get('status', 'unknown')}")
    current_app.logger.debug("Sync status for project %s: %d sessions found", project.id, len(sessions))
    return jsonify({
        'success': True,
        'repository': repo_info,
        'history': history,
        'sessions': sessions
    }), 200


@api_uploads_bp.route('/projects/<int:project_id>/files/tree', methods=['GET'])
@login_required
def list_project_files(project_id: int):
    _get_project_with_access(project_id)
    files = list_repo_files(project_id)
    return jsonify({'success': True, 'files': files}), 200


@api_uploads_bp.route('/projects/<int:project_id>/files/sign', methods=['POST'])
@login_required
def sign_project_file(project_id: int):
    _get_project_with_access(project_id)
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Richiesta non valida (JSON richiesto).'}), 400
    relative_path = request.json.get('path')
    try:
        sanitized = sanitize_workspace_path(relative_path)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    file_path = get_repo_file_path(project_id, sanitized)
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'error': 'File non trovato.'}), 404
    token = generate_file_token(project_id, sanitized)
    return jsonify({'success': True, 'token': token}), 200


@api_uploads_bp.route('/projects/<int:project_id>/files', defaults={'requested_path': ''}, methods=['GET'])
@api_uploads_bp.route('/projects/<int:project_id>/files/<path:requested_path>', methods=['GET'])
@login_required
def download_project_file(project_id: int, requested_path: str):
    _get_project_with_access(project_id)
    token = request.args.get('token')
    if not requested_path:
        return jsonify({'success': False, 'error': 'Specificare un percorso file.'}), 400
    if not token:
        return jsonify({'success': False, 'error': 'Token mancante.'}), 400
    try:
        token_data = verify_file_token(token)
    except SignatureExpired:
        return jsonify({'success': False, 'error': 'Token scaduto.'}), 410
    except BadSignature:
        return jsonify({'success': False, 'error': 'Token non valido.'}), 400

    try:
        sanitized_requested_path = sanitize_workspace_path(requested_path)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    if token_data.get('project_id') != project_id or token_data.get('path') != sanitized_requested_path:
        return jsonify({'success': False, 'error': 'Token non valido per questo file.'}), 403

    file_path = get_repo_file_path(project_id, sanitized_requested_path)
    if not os.path.exists(file_path):
        return jsonify({'success': False, 'error': 'File non trovato.'}), 404

    mime, _ = mimetypes.guess_type(file_path)
    return send_file(file_path, mimetype=mime or 'application/octet-stream', as_attachment=False)

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


@api_uploads_bp.route('/projects/<int:project_id>/tasks/<int:task_id>/submit', methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def submit_task_solution(project_id: int, task_id: int):
    """
    Endpoint per sottomettere una soluzione (ZIP) per un task.
    Crea automaticamente una Pull Request su GitHub.
    """
    project = _get_project_with_access(project_id)
    task = Task.query.get_or_404(task_id)
    
    if task.project_id != project.id:
        abort(404, description="Task non appartenente al progetto.")
        
    if task.status != 'open' and task.status != 'in_progress':
        return jsonify({'success': False, 'error': 'Il task non è aperto per sottomissioni.'}), 400

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Nessun file ZIP caricato.'}), 400

    zip_file = request.files['file']
    if not zip_file.filename or not zip_file.filename.endswith('.zip'):
        return jsonify({'success': False, 'error': 'Il file deve essere un archivio ZIP.'}), 400

    # Salva ZIP in temp
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, get_safe_filename(zip_file.filename))
    zip_file.save(zip_path)
    
    try:
        # Crea record Solution (pending)
        solution = Solution(
            task_id=task.id,
            submitted_by_user_id=current_user.id,
            solution_content="ZIP Submission via KickThisUSS",
            content_type='software', # Assumiamo software per ora
            github_pr_status='pending'
        )
        db.session.add(solution)
        db.session.commit()
        
        # ⭐ NUOVO: AI Analysis del ZIP (prima di GitHub sync)
        ai_score_added = False
        try:
            from app.services.zip_processor import ZipProcessor
            from app.ai_services import analyze_solution_content
            
            processor = ZipProcessor()
            with open(zip_path, 'rb') as f:
                extracted_files = processor.extract_zip(f)
            
            code_summary = processor.extract_code_summary(extracted_files, max_chars=8000)
            
            if code_summary:
                analysis_results = analyze_solution_content(
                    task.title,
                    task.description,
                    code_summary
                )
                
                if analysis_results and analysis_results.get('error') is None:
                    solution.ai_coherence_score = analysis_results.get('coherence_score')
                    solution.ai_completeness_score = analysis_results.get('completeness_score')
                    db.session.commit()
                    ai_score_added = True
                    current_app.logger.info(
                        f"AI analysis for API ZIP solution #{solution.id}: "
                        f"coherence={solution.ai_coherence_score}"
                    )
        except Exception as ai_error:
            current_app.logger.warning(f"AI analysis failed (non-critical): {ai_error}")
        
        # Avvia sync con GitHub

        if GITHUB_SYNC_AVAILABLE:
            sync_service = GitHubSyncService()
            result = sync_service.submit_solution_zip(project, task, current_user, zip_path)
            
            if result.get('success'):
                solution.pull_request_url = result.get('pr_url')
                solution.github_pr_number = result.get('pr_number')
                solution.github_branch = result.get('branch')
                solution.github_commit_sha = result.get('commit_sha')
                solution.github_pr_status = 'open'
                solution.is_approved = False # Richiede review
                
                # Aggiorna stato task se necessario
                if task.status == 'open':
                    task.status = 'submitted'
                
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'solution_id': solution.id,
                    'pr_url': solution.pull_request_url,
                    'message': 'Soluzione inviata con successo! Pull Request creata.'
                }), 200
            else:
                # Fallimento sync
                db.session.delete(solution)
                db.session.commit()
                return jsonify({'success': False, 'error': result.get('error', 'Errore sconosciuto durante sync GitHub')}), 500
        else:
            return jsonify({'success': False, 'error': 'Integrazione GitHub non disponibile.'}), 503
            
    except Exception as e:
        current_app.logger.error(f"Error submitting solution: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

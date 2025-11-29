import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from flask import current_app

from app.extensions import db
from app.models import Project, ProjectRepository
from app.workspace_utils import (
    append_history_entry,
    load_session_metadata,
    sanitize_workspace_path,
    save_session_metadata,
    session_dir as ws_session_dir,
    synced_repo_dir
)
from app.services.notification_service import NotificationService
from .managed_repo_service import ManagedRepoService
from .github_sync_service import GitHubSyncService
from .git_sync_service import GitSyncService

logger = logging.getLogger(__name__)


class WorkspaceSyncService:
    """
    Sincronizza i file caricati dagli utenti con il repository gestito.
    Usa git commands quando possibile (più veloce), fallback a GitHub API.
    """

    def __init__(self):
        self.managed_repo = ManagedRepoService()
        self.github_sync = GitHubSyncService()
        self.git_sync = GitSyncService()

    def sync_session(self, project: Project, session_id: str, initiated_by: Optional[int] = None) -> Dict[str, any]:
        """
        Sincronizza una sessione di upload con il repository gestito.
        Ottimizzato per performance con batch upload e lazy loading.
        """
        import time
        
        session_directory = ws_session_dir(project.id, session_id)
        metadata = load_session_metadata(session_directory)
        if not metadata:
            raise ValueError("Session metadata not found.")

        if metadata.get('status') == 'completed':
            return metadata

        # Check for stale "syncing" status (timeout: 10 minutes)
        if metadata.get('status') == 'syncing':
            sync_started = metadata.get('sync_started_at')
            if sync_started:
                from dateutil import parser as date_parser
                try:
                    started_time = date_parser.isoparse(sync_started)
                    elapsed = (datetime.now(timezone.utc) - started_time).total_seconds()
                    if elapsed > 600:  # 10 minutes timeout
                        logger.warning(
                            f"Session {session_id} for project {project.id} stuck in 'syncing' "
                            f"for {elapsed:.0f}s - recovering by marking as 'error'"
                        )
                        metadata['status'] = 'error'
                        metadata['error'] = f'Sync timeout after {elapsed:.0f}s (server restart or crash)'
                        metadata['sync_finished_at'] = datetime.now(timezone.utc).isoformat()
                        save_session_metadata(session_directory, metadata)
                        return metadata
                except Exception as parse_err:
                    logger.warning(f"Could not parse sync_started_at: {parse_err}")

        if initiated_by and not metadata.get('initiated_by'):
            metadata['initiated_by'] = initiated_by

        metadata['status'] = 'syncing'
        metadata['sync_started_at'] = datetime.now(timezone.utc).isoformat()
        save_session_metadata(session_directory, metadata)

        # Wrap entire sync process in try-except to ensure status is always updated
        try:
            # Raccogli file (con lazy loading per file grandi)
            collect_start = time.time()
            files = self._collect_files(session_directory, lazy=True)
            collect_elapsed = time.time() - collect_start
            
            # Carica contenuto per file lazy prima di inviare a GitHub
            load_start = time.time()
            for file_data in files:
                if file_data.get('lazy') and file_data.get('full_path'):
                    # Carica contenuto solo quando necessario
                    try:
                        with open(file_data['full_path'], 'rb') as fh:
                            file_data['content'] = fh.read()
                        file_data['lazy'] = False
                    except Exception as e:
                        logger.error(f"Failed to load lazy file {file_data.get('path')}: {e}")
            load_elapsed = time.time() - load_start
            
            total_files = len(files)
            total_size = sum(f.get('size', 0) for f in files)
            
            logger.info(
                f"Session {session_id} for project {project.id}: "
                f"{total_files} files ({total_size / 1024 / 1024:.2f} MB) "
                f"collected in {collect_elapsed:.2f}s, loaded in {load_elapsed:.2f}s"
            )
            
            success = True
            error_message = None
            sync_method = 'none'
            sync_elapsed = 0

            if files:
                if self.github_sync.is_enabled():
                    try:
                        self.managed_repo.initialize_managed_repository(project)
                        
                        # PRIORITÀ: Prova git sync (più veloce per upload massivi)
                        if self.git_sync.is_enabled():
                            logger.info(f"Using git sync for project {project.id} session {session_id}")
                            sync_start = time.time()
                            git_result = self.git_sync.sync_workspace_from_directory(
                                project, session_directory, initiated_by
                            )
                            sync_elapsed = time.time() - sync_start
                            sync_method = git_result.get('method', 'git')
                            
                            if git_result.get('status') == 'success':
                                success = True
                                logger.info(
                                    f"Git sync completed for project {project.id} session {session_id}: "
                                    f"{git_result.get('files_synced', 0)} files in {sync_elapsed:.2f}s "
                                    f"({git_result.get('files_synced', 0) / sync_elapsed:.1f} files/sec if files > 0)"
                                )
                            else:
                                # Git sync fallito, fallback a GitHub API
                                logger.warning(
                                    f"Git sync failed, falling back to GitHub API: {git_result.get('message')}"
                                )
                                sync_start = time.time()
                                sync_result = self.github_sync.sync_multiple_files(project, files)
                                sync_elapsed = time.time() - sync_start
                                sync_method = sync_result.get('method', 'api_fallback')
                                
                                if sync_result.get('failed'):
                                    success = False
                                    error_message = '; '.join(sync_result.get('errors', []))
                        else:
                            # Git non disponibile, usa GitHub API
                            logger.info(f"Git not available, using GitHub API for project {project.id} session {session_id}")
                            sync_start = time.time()
                            sync_result = self.github_sync.sync_multiple_files(project, files)
                            sync_elapsed = time.time() - sync_start
                            sync_method = sync_result.get('method', 'api')
                            
                            if sync_result.get('failed'):
                                success = False
                                error_message = '; '.join(sync_result.get('errors', []))
                            
                            logger.info(
                                f"GitHub API sync for project {project.id} session {session_id}: "
                                f"{sync_result.get('success', 0)}/{total_files} files "
                                f"using {sync_method} method in {sync_elapsed:.2f}s "
                                f"({sync_result.get('success', 0) / sync_elapsed:.1f} files/sec if success > 0)"
                            )
                    except Exception as exc:
                        success = False
                        error_message = str(exc)
                        logger.error(
                            f"Sync failed for project {project.id} session {session_id}: {exc}",
                            exc_info=True
                        )
                else:
                    logger.info("GitHub disabled – session %s stored locally for project %s", session_id, project.id)
                
                if success:
                    # Mirror locale (parallelizzato)
                    mirror_start = time.time()
                    self._mirror_files_locally(project, files)
                    mirror_elapsed = time.time() - mirror_start
                    logger.debug(
                        f"Local mirror for project {project.id} session {session_id}: "
                        f"{total_files} files in {mirror_elapsed:.2f}s"
                    )
            else:
                success = False
                error_message = "Nessun file valido nella sessione."

            total_elapsed = time.time() - collect_start
            
            metadata['sync_finished_at'] = datetime.now(timezone.utc).isoformat()
            metadata['sync_performance'] = {
                'total_elapsed_seconds': total_elapsed,
                'collect_elapsed_seconds': collect_elapsed,
                'load_elapsed_seconds': load_elapsed,
                'sync_elapsed_seconds': sync_elapsed,
                'sync_method': sync_method,
                'files_count': total_files,
                'total_size_bytes': total_size
            }
            
            if success:
                metadata['status'] = 'completed'
                metadata['error'] = None
                self._update_project_repository(project)
                NotificationService.notify_workspace_sync_completed(project, metadata, initiated_by)
                logger.info(
                    f"Session {session_id} for project {project.id} completed successfully "
                    f"in {total_elapsed:.2f}s (method: {sync_method})"
                )
            else:
                metadata['status'] = 'error'
                metadata['error'] = error_message
                NotificationService.notify_workspace_sync_failed(project, metadata, initiated_by)
                logger.error(
                    f"Session {session_id} for project {project.id} failed: {error_message}"
                )

            save_session_metadata(session_directory, metadata)
            self._record_history_entry(project, metadata)

            return metadata
            
        except Exception as unexpected_exc:
            # Catch any unexpected exception and mark session as error
            logger.error(
                f"Unexpected exception in sync_session for project {project.id} session {session_id}: {unexpected_exc}",
                exc_info=True
            )
            metadata['status'] = 'error'
            metadata['error'] = f'Unexpected error: {str(unexpected_exc)}'
            metadata['sync_finished_at'] = datetime.now(timezone.utc).isoformat()
            save_session_metadata(session_directory, metadata)
            raise  # Re-raise to propagate error

    def _collect_files(self, session_directory: str, lazy: bool = False) -> List[Dict[str, any]]:
        """
        Raccoglie file dalla sessione directory.
        
        Args:
            session_directory: Directory della sessione
            lazy: Se True, per file >= 10MB carica solo path + size (non content)
        
        Returns:
            Lista di dict con 'path', 'content' (o None se lazy), 'relative_path', 'message'
        """
        files = []
        LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB
        
        for root, _, filenames in os.walk(session_directory):
            for filename in filenames:
                if filename == 'metadata.json':
                    continue
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, session_directory).replace('\\', '/')
                
                # Ottieni dimensione file
                file_size = os.path.getsize(full_path)
                
                # Per file grandi con lazy=True, carica solo metadata
                if lazy and file_size >= LARGE_FILE_THRESHOLD:
                    files.append({
                        'path': f"workspace/{rel_path}",
                        'relative_path': rel_path,
                        'content': None,  # Lazy loading - carica quando necessario
                        'full_path': full_path,  # Salva path per lazy loading
                        'size': file_size,
                        'message': f"Add {rel_path}",
                        'lazy': True
                    })
                else:
                    # Carica contenuto in memoria (file piccoli o lazy=False)
                    with open(full_path, 'rb') as fh:
                        content = fh.read()
                    files.append({
                        'path': f"workspace/{rel_path}",
                        'relative_path': rel_path,
                        'content': content,
                        'size': file_size,
                        'message': f"Add {rel_path}",
                        'lazy': False
                    })
        
        return files

    def _mirror_files_locally(self, project: Project, files: List[Dict[str, any]]):
        """
        Crea mirror locale dei file sincronizzati.
        Ottimizzato per file grandi usando shutil.copy2 e parallelizzazione.
        """
        import shutil
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        repo_dir = synced_repo_dir(project.id)
        
        def copy_file(file_data):
            """Helper per copiare un singolo file."""
            relative_path = file_data.get('relative_path') or file_data.get('path')
            if not relative_path:
                return False
            
            if relative_path.startswith('workspace/'):
                relative_path = relative_path[len('workspace/'):]
            
            try:
                sanitized = sanitize_workspace_path(relative_path)
            except ValueError:
                logger.warning("Skipping invalid workspace path during mirror: %s", relative_path)
                return False
            
            dest_path = os.path.join(repo_dir, *sanitized.split('/'))
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Se abbiamo full_path (lazy loading), usa shutil.copy2 (più efficiente)
            if file_data.get('lazy') and file_data.get('full_path'):
                try:
                    shutil.copy2(file_data['full_path'], dest_path)
                    return True
                except Exception as e:
                    logger.warning(f"Failed to copy file {relative_path}: {e}")
                    return False
            else:
                # Altrimenti scrivi da content in memoria
                content = file_data.get('content', b'')
                if content:
                    try:
                        with open(dest_path, 'wb') as handle:
                            handle.write(content)
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to write file {relative_path}: {e}")
                        return False
            
            return False
        
        # Parallelizza I/O per file multipli (max 4 workers)
        MAX_WORKERS = 4
        copied = 0
        failed = 0
        
        if len(files) > 1:
            # Usa ThreadPoolExecutor per parallelizzare
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_file = {executor.submit(copy_file, f): f for f in files}
                for future in as_completed(future_to_file):
                    if future.result():
                        copied += 1
                    else:
                        failed += 1
        else:
            # Singolo file - no need per threading overhead
            if copy_file(files[0]) if files else False:
                copied = 1
            else:
                failed = 1
        
        if failed > 0:
            logger.warning(f"Failed to mirror {failed} files locally for project {project.id}")
        else:
            logger.debug(f"Mirrored {copied} files locally for project {project.id}")

    def _record_history_entry(self, project: Project, metadata: Dict[str, any]):
        files = metadata.get('files', [])
        total_size = metadata.get('total_size') or sum(file.get('size', 0) for file in files)
        entry = {
            'session_id': metadata.get('session_id'),
            'status': metadata.get('status'),
            'type': metadata.get('type', 'manual'),
            'file_count': len(files),
            'total_size': total_size,
            'completed_at': metadata.get('sync_finished_at'),
            'initiated_by': metadata.get('initiated_by'),
            'error': metadata.get('error')
        }
        append_history_entry(project.id, entry)

    def _update_project_repository(self, project: Project):
        repo_record = ProjectRepository.query.filter_by(project_id=project.id).first()
        if not repo_record:
            repo_record = self.managed_repo.initialize_managed_repository(project)

        if repo_record:
            repo_record.last_sync_at = datetime.now(timezone.utc)
            repo_record.status = 'ready'
            with db.session.begin_nested():
                db.session.add(repo_record)


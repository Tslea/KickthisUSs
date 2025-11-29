# app/services/git_sync_service.py
"""
Git Sync Service - Upload workspace usando git commands invece di GitHub API.
Più veloce, più semplice, più robusto per upload massivi.
"""

import logging
import os
import subprocess
import tempfile
import shutil
import threading
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from flask import current_app
from app.models import Project
from app.services.github_sync_service import GitHubSyncService

logger = logging.getLogger(__name__)


class GitSyncService:
    """
    Servizio per sincronizzare workspace su GitHub usando git commands.
    Sostituisce GitHub API per upload massivi (più veloce e robusto).
    """
    
    def __init__(self):
        self.github_sync = GitHubSyncService()
        self.enabled = self.github_sync.is_enabled()
    
    def is_enabled(self) -> bool:
        """Verifica se il servizio è abilitato."""
        return self.enabled and self._check_git_available()
    
    def _check_git_available(self) -> bool:
        """Verifica se git è disponibile nel sistema."""
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            logger.warning("Git command not available - falling back to GitHub API")
            return False
    
    def sync_workspace_from_directory(
        self,
        project: Project,
        source_directory: str,
        initiated_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sincronizza un'intera directory workspace su GitHub usando git commands.
        
        Args:
            project: Progetto da sincronizzare
            source_directory: Directory locale con i file da caricare
            initiated_by: ID utente che ha avviato il sync
        
        Returns:
            Dict con risultati: {'status': str, 'message': str, 'commit_sha': str, 'files_synced': int}
        """
        if not self.is_enabled():
            return {
                'status': 'disabled',
                'message': 'Git sync is disabled (GitHub disabled or git not available)',
                'method': 'git_disabled'
            }
        
        # Assicura che il repository esista (usa logica esistente)
        if not project.github_repo_name:
            repo_info = self.github_sync.setup_project_repository(project)
            if not repo_info:
                return {
                    'status': 'error',
                    'message': 'Failed to setup GitHub repository',
                    'method': 'git'
                }
        
        temp_repo_dir = None
        try:
            # Crea directory temporanea per clone
            temp_repo_dir = tempfile.mkdtemp(prefix=f"git_sync_{project.id}_")
            logger.info(f"Created temp directory for git sync: {temp_repo_dir}")
            
            # Ottieni token GitHub
            github_token = current_app.config.get('GITHUB_TOKEN')
            if not github_token:
                return {
                    'status': 'error',
                    'message': 'GitHub token not configured',
                    'method': 'git'
                }
            
            # Costruisci URL con token per autenticazione
            repo_url = f"https://github.com/{project.github_repo_name}.git"
            repo_url_with_token = repo_url.replace(
                'https://github.com/',
                f'https://{github_token}@github.com/'
            )
            
            # 1. Clone repository
            logger.info(f"Cloning repository {project.github_repo_name}...")
            clone_result = subprocess.run(
                ['git', 'clone', repo_url_with_token, temp_repo_dir],
                capture_output=True,
                text=True,
                timeout=300  # 5 minuti timeout
            )
            
            if clone_result.returncode != 0:
                error_msg = clone_result.stderr or clone_result.stdout or "Unknown error"
                logger.error(f"Git clone failed: {error_msg}")
                return {
                    'status': 'error',
                    'message': f'Git clone failed: {error_msg}',
                    'method': 'git'
                }
            
            # 2. Copia file dalla directory sorgente al repository
            logger.info(f"Copying files from {source_directory} to repository...")
            files_copied = self._copy_files_to_repo(source_directory, temp_repo_dir)
            
            if files_copied == 0:
                logger.warning("No files to sync")
                return {
                    'status': 'info',
                    'message': 'No files to sync',
                    'files_synced': 0,
                    'method': 'git'
                }
            
            # 3. Configura git user (necessario per commit)
            subprocess.run(
                ['git', '-C', temp_repo_dir, 'config', 'user.name', 'KickthisUSs Bot'],
                check=False,
                capture_output=True
            )
            subprocess.run(
                ['git', '-C', temp_repo_dir, 'config', 'user.email', 'bot@kickthisuss.com'],
                check=False,
                capture_output=True
            )
            
            # 4. Git add
            logger.info("Staging files...")
            add_result = subprocess.run(
                ['git', '-C', temp_repo_dir, 'add', '.'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if add_result.returncode != 0:
                logger.warning(f"Git add had warnings: {add_result.stderr}")
            
            # 5. Git commit
            commit_message = f"Upload workspace: {files_copied} files via KickthisUSs"
            logger.info(f"Committing changes: {commit_message}")
            commit_result = subprocess.run(
                ['git', '-C', temp_repo_dir, 'commit', '-m', commit_message],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if commit_result.returncode != 0:
                # Potrebbe essere che non ci sono cambiamenti (tutto già committato)
                if 'nothing to commit' in commit_result.stdout.lower():
                    logger.info("No changes to commit (files already up to date)")
                    # Ottieni ultimo commit SHA
                    log_result = subprocess.run(
                        ['git', '-C', temp_repo_dir, 'log', '-1', '--format=%H'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    commit_sha = log_result.stdout.strip() if log_result.returncode == 0 else None
                    
                    return {
                        'status': 'success',
                        'message': f'Workspace already up to date ({files_copied} files)',
                        'commit_sha': commit_sha,
                        'files_synced': files_copied,
                        'method': 'git'
                    }
                else:
                    error_msg = commit_result.stderr or commit_result.stdout or "Unknown error"
                    logger.error(f"Git commit failed: {error_msg}")
                    return {
                        'status': 'error',
                        'message': f'Git commit failed: {error_msg}',
                        'method': 'git'
                    }
            
            # Ottieni commit SHA
            log_result = subprocess.run(
                ['git', '-C', temp_repo_dir, 'log', '-1', '--format=%H'],
                capture_output=True,
                text=True,
                timeout=10
            )
            commit_sha = log_result.stdout.strip() if log_result.returncode == 0 else None
            
            # 6. Git push
            logger.info("Pushing to GitHub...")
            push_result = subprocess.run(
                ['git', '-C', temp_repo_dir, 'push', 'origin', 'main'],
                capture_output=True,
                text=True,
                timeout=300  # 5 minuti timeout
            )
            
            if push_result.returncode != 0:
                # Prova con 'master' se 'main' fallisce
                push_result = subprocess.run(
                    ['git', '-C', temp_repo_dir, 'push', 'origin', 'master'],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            
            if push_result.returncode != 0:
                error_msg = push_result.stderr or push_result.stdout or "Unknown error"
                logger.error(f"Git push failed: {error_msg}")
                return {
                    'status': 'error',
                    'message': f'Git push failed: {error_msg}',
                    'commit_sha': commit_sha,
                    'method': 'git'
                }
            
            logger.info(
                f"✅ Git sync completed for project {project.id}: "
                f"{files_copied} files in commit {commit_sha}"
            )
            
            return {
                'status': 'success',
                'message': f'Workspace synchronized: {files_copied} files in 1 commit',
                'commit_sha': commit_sha,
                'commit_url': f"https://github.com/{project.github_repo_name}/commit/{commit_sha}" if commit_sha else None,
                'files_synced': files_copied,
                'method': 'git'
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Git command timeout for project {project.id}")
            return {
                'status': 'error',
                'message': 'Git command timeout (operation took too long)',
                'method': 'git'
            }
        except Exception as e:
            logger.error(f"❌ Git sync failed for project {project.id}: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f'Git sync failed: {str(e)}',
                'method': 'git'
            }
        finally:
            # Cleanup: rimuovi directory temporanea
            if temp_repo_dir and os.path.exists(temp_repo_dir):
                try:
                    shutil.rmtree(temp_repo_dir, ignore_errors=True)
                    logger.debug(f"Cleaned up temp directory: {temp_repo_dir}")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup temp directory: {cleanup_err}")
    
    def _copy_files_to_repo(self, source_dir: str, repo_dir: str) -> int:
        """
        Copia file dalla directory sorgente al repository.
        Esclude file e cartelle non necessari (.git, __pycache__, etc.)
        
        Returns:
            Numero di file copiati
        """
        from app.workspace_utils import should_sync_to_github, is_file_safe
        
        files_copied = 0
        workspace_dir = os.path.join(repo_dir, 'workspace')
        os.makedirs(workspace_dir, exist_ok=True)
        
        # Lista di cartelle da escludere
        exclude_dirs = {'__pycache__', '.venv', 'venv', 'node_modules', '.git', 'dist', 'build', '.idea', '.vscode'}
        
        for root, dirs, files in os.walk(source_dir):
            # Filtra cartelle da escludere
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            # Calcola path relativo
            rel_root = os.path.relpath(root, source_dir)
            if rel_root == '.':
                dest_root = workspace_dir
            else:
                dest_root = os.path.join(workspace_dir, rel_root.replace('\\', '/'))
            
            os.makedirs(dest_root, exist_ok=True)
            
            for filename in files:
                if filename == 'metadata.json':
                    continue
                
                source_path = os.path.join(root, filename)
                relative_path = os.path.join(rel_root, filename).replace('\\', '/') if rel_root != '.' else filename
                
                # Security check
                is_safe, _ = is_file_safe(relative_path)
                if not is_safe:
                    logger.debug(f"Skipping unsafe file: {relative_path}")
                    continue
                
                # Sync filter
                should_sync, _ = should_sync_to_github(relative_path)
                if not should_sync:
                    logger.debug(f"Skipping filtered file: {relative_path}")
                    continue
                
                # Copia file
                dest_path = os.path.join(dest_root, filename)
                try:
                    shutil.copy2(source_path, dest_path)
                    files_copied += 1
                except Exception as e:
                    logger.warning(f"Failed to copy file {relative_path}: {e}")
        
        return files_copied
    
    def sync_workspace_async(
        self,
        project: Project,
        source_directory: str,
        initiated_by: Optional[int] = None
    ) -> threading.Thread:
        """
        Avvia sync workspace in background thread.
        
        Returns:
            Thread object (può essere usato per join/wait)
        """
        def _sync():
            try:
                result = self.sync_workspace_from_directory(project, source_directory, initiated_by)
                logger.info(f"Async git sync completed: {result.get('status')}")
            except Exception as e:
                logger.error(f"Async git sync failed: {e}", exc_info=True)
        
        thread = threading.Thread(target=_sync, daemon=True)
        thread.start()
        return thread


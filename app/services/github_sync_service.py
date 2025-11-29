# app/services/github_sync_service.py
"""
GitHub Synchronization Service
Gestisce la sincronizzazione automatica tra KICKTHISUSS e GitHub.

DESIGN PRINCIPLES:
1. L'utente NON vede mai GitHub - tutto è automatico
2. Se GitHub fallisce, l'app continua a funzionare (fallback locale)
3. La sincronizzazione è SEMPRE attiva se GITHUB_ENABLED=true in config
4. Zero configurazione utente - completamente trasparente
5. Database minimale - solo github_repo_name salvato
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from flask import current_app

from .github_service import GitHubService, GitHubServiceError
from app.models import Project, Task, User, db
from app.services.zip_processor import ZipProcessor
import shutil
import tempfile

logger = logging.getLogger(__name__)


class GitHubSyncService:
    """
    Servizio di sincronizzazione automatica tra KICKTHISUSS e GitHub.
    Completamente trasparente per l'utente.
    """
    
    def __init__(self):
        """Inizializza il servizio di sincronizzazione."""
        self.github_service = GitHubService()
        self.enabled = self.github_service.is_enabled()
    
    def is_enabled(self) -> bool:
        """Verifica se il servizio è abilitato globalmente."""
        return self.enabled
    
    def setup_project_repository(
        self, 
        project: Project
    ) -> Optional[Dict[str, Any]]:
        """
        Setup repository GitHub per un progetto.
        Crea il repository se non esiste, oppure lo recupera.
        Chiamato automaticamente quando necessario - NO user intervention.
        
        Args:
            project: Oggetto Project da sincronizzare
        
        Returns:
            Dict con informazioni del repository o None se errore/disabilitato
        """
        if not self.is_enabled():
            logger.debug(f"GitHub sync disabled globally - skipping setup for project {project.id}")
            return None
        
        try:
            # Se il repository esiste già, recuperalo
            if project.github_repo_name:
                repo = self.github_service.get_repository(project.github_repo_name)
                if repo:
                    logger.debug(f"Retrieved existing repository for project {project.id}: {project.github_repo_name}")
                    return {
                        'name': repo.name,
                        'full_name': repo.full_name,
                        'html_url': repo.html_url,
                        'exists': True
                    }
            
            # Crea nuovo repository
            repo_name = self._generate_repo_name(project)
            description = self._generate_repo_description(project)
            
            # Determina gitignore template basato sul tipo di progetto
            gitignore_template = self._get_gitignore_template(project)
            
            repo_info = self.github_service.create_repository(
                name=repo_name,
                description=description,
                private=project.private,  # Usa la privacy del progetto
                auto_init=True,
                gitignore_template=gitignore_template
            )
            
            if repo_info:
                # Salva solo il nome del repository nel database
                project.github_repo_name = repo_info['full_name']
                db.session.commit()
                
                logger.info(f"Created GitHub repository for project {project.id}: {repo_info['full_name']}")
                
                # Crea README.md iniziale con informazioni del progetto
                self._create_initial_readme(project, repo_info['name'])
                
                return repo_info
            
            return None
            
        except GitHubServiceError as e:
            logger.error(f"GitHub error setting up repository for project {project.id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error setting up repository for project {project.id}: {e}")
            return None
    
    def sync_file(
        self,
        project: Project,
        file_path: str,
        content: bytes,
        commit_message: Optional[str] = None
    ) -> bool:
        """
        Sincronizza un singolo file con GitHub.
        Chiamato automaticamente dopo ogni upload locale.
        
        Args:
            project: Progetto a cui appartiene il file
            file_path: Percorso del file nel repository (es. 'src/main.py')
            content: Contenuto del file come bytes
            commit_message: Messaggio di commit personalizzato
        
        Returns:
            True se sincronizzato con successo, False altrimenti
        """
        if not self.is_enabled():
            logger.debug(f"GitHub sync disabled globally - skipping file sync")
            return False
        
        # Se il repository non esiste, crealo automaticamente
        if not project.github_repo_name:
            repo_info = self.setup_project_repository(project)
            if not repo_info:
                logger.warning(f"Could not setup repository for project {project.id} - file not synced")
                return False
        
        try:
            result = self.github_service.upload_file(
                repo_name=project.github_repo_name,
                file_path=file_path,
                content=content,
                commit_message=commit_message
            )
            
            if result:
                logger.info(f"Synced file {file_path} to GitHub for project {project.id}")
                return True
            
            return False
            
        except GitHubServiceError as e:
            logger.error(f"GitHub error syncing file for project {project.id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error syncing file for project {project.id}: {e}")
            return False
    
    def sync_multiple_files(
        self,
        project: Project,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Sincronizza multipli file con GitHub.
        Usa batch upload (Tree API) quando possibile per performance 10-30x migliori.
        Fallback automatico a metodo sequenziale se batch fallisce.
        
        Args:
            project: Progetto a cui appartengono i file
            files: Lista di dict con keys: 'path', 'content', 'message' (opzionale)
        
        Returns:
            Dict con risultati: {'success': int, 'failed': int, 'errors': List[str], 'method': str, 'blocked': List[str]}
        """
        from app.workspace_utils import is_file_safe, should_sync_to_github
        
        results = {
            'success': 0,
            'failed': 0,
            'errors': [],
            'method': 'unknown',
            'blocked': [],  # File bloccati per sicurezza
            'ignored': []   # File ignorati (build artifacts, etc)
        }
        
        if not self.is_enabled():
            results['errors'].append("GitHub sync is disabled globally")
            return results
        
        # Valida input + SECURITY CHECK + SYNC FILTER
        valid_files = []
        for file_info in files:
            file_path = file_info.get('path')
            content = file_info.get('content')
            
            if not file_path or content is None:
                results['failed'] += 1
                results['errors'].append(f"Invalid file info: {file_info}")
                continue
            
            # 🔒 SECURITY: Verifica che il file sia sicuro
            is_safe, safety_reason = is_file_safe(file_path)
            if not is_safe:
                results['blocked'].append(f"{file_path} ({safety_reason})")
                logger.warning(f"🔒 SECURITY: File bloccato da sync: {file_path} - {safety_reason}")
                continue
            
            # 🚫 SYNC FILTER: Verifica se il file deve essere sincronizzato
            should_sync, sync_reason = should_sync_to_github(file_path)
            if not should_sync:
                results['ignored'].append(f"{file_path} ({sync_reason})")
                logger.debug(f"⏭️ SYNC: File ignorato: {file_path} - {sync_reason}")
                continue
            
            valid_files.append(file_info)
        
        if not valid_files:
            return results
        
        # Assicura che il repository esista
        if not project.github_repo_name:
            repo_info = self.setup_project_repository(project)
            if not repo_info:
                results['errors'].append("Could not setup repository for project")
                results['failed'] = len(valid_files)
                return results
        
        # PRIORITÀ: Prova batch upload (veloce) - solo se > 1 file o se esplicitamente richiesto
        if len(valid_files) > 1:  # Batch ha senso solo con > 1 file
            try:
                import time
                start_time = time.time()
                
                # Prepara files per batch upload
                batch_files = []
                for file_info in valid_files:
                    batch_files.append({
                        'path': file_info.get('path'),
                        'content': file_info.get('content', b''),
                        'mode': '100644'  # Default: file normale
                    })
                
                # Genera commit message intelligente
                commit_message = self._generate_batch_commit_message(valid_files)
                
                # Limita batch a 100 file alla volta (se più file, dividi in batch multipli)
                BATCH_SIZE = 100
                total_success = 0
                total_failed = 0
                
                for i in range(0, len(batch_files), BATCH_SIZE):
                    batch_chunk = batch_files[i:i + BATCH_SIZE]
                    
                    batch_result = self.github_service.upload_files_batch(
                        repo_name=project.github_repo_name,
                        files=batch_chunk,
                        commit_message=commit_message if i == 0 else f"{commit_message} (batch {i // BATCH_SIZE + 1})",
                        branch='main'  # TODO: leggere branch da ProjectRepository se disponibile
                    )
                    
                    if batch_result:
                        total_success += len(batch_chunk)
                        logger.info(
                            f"Batch upload successful for project {project.id}: "
                            f"{len(batch_chunk)} files in {batch_result.get('elapsed_seconds', 0):.2f}s"
                        )
                    else:
                        total_failed += len(batch_chunk)
                        results['errors'].append(f"Batch upload failed for chunk {i // BATCH_SIZE + 1}")
                
                elapsed = time.time() - start_time
                
                if total_success > 0:
                    results['success'] = total_success
                    results['failed'] = total_failed
                    results['method'] = 'batch'
                    logger.info(
                        f"Batch upload completed for project {project.id}: "
                        f"{total_success} files in {elapsed:.2f}s "
                        f"({len(valid_files) / elapsed:.1f} files/sec)"
                    )
                    return results
                else:
                    # Batch completamente fallito - fallback a sequenziale
                    logger.warning(
                        f"Batch upload failed for project {project.id}, "
                        f"falling back to sequential method"
                    )
            
            except Exception as e:
                logger.warning(
                    f"Batch upload failed for project {project.id}, "
                    f"falling back to sequential: {e}",
                    exc_info=True
                )
                # Continua con fallback sequenziale
        
        # FALLBACK: Metodo sequenziale esistente (non rimuovere!)
        import time
        start_time = time.time()
        
        for file_info in valid_files:
            file_path = file_info.get('path')
            content = file_info.get('content')
            message = file_info.get('message')
            
            success = self.sync_file(project, file_path, content, message)
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"Failed to sync: {file_path}")
        
        elapsed = time.time() - start_time
        results['method'] = 'sequential'
        logger.info(
            f"Sequential upload completed for project {project.id}: "
            f"{results['success']} files in {elapsed:.2f}s "
            f"({results['success'] / elapsed:.1f} files/sec if success > 0)"
        )
        
        return results
    
    def _generate_batch_commit_message(self, files: List[Dict[str, Any]]) -> str:
        """
        Genera un commit message intelligente per batch upload.
        
        Args:
            files: Lista di file da committare
        
        Returns:
            Commit message
        """
        file_count = len(files)
        
        # Se c'è un messaggio comune nei file, usalo
        messages = [f.get('message') for f in files if f.get('message')]
        if messages and len(set(messages)) == 1:
            # Tutti i file hanno lo stesso messaggio
            base_message = messages[0]
            if file_count > 1:
                return f"Upload {file_count} files: {base_message}"
            return base_message
        
        # Altrimenti genera messaggio generico
        if file_count == 1:
            file_path = files[0].get('path', 'file')
            return f"Upload {file_path} via KickthisUSs"
        else:
            return f"Upload {file_count} files via KickthisUSs"
    
    def get_project_sync_status(self, project: Project) -> Dict[str, Any]:
        """
        Ottieni lo stato della sincronizzazione per un progetto.
        
        Args:
            project: Progetto da verificare
        
        Returns:
            Dict con informazioni sullo stato sync
        """
        if not self.is_enabled():
            return {
                'github_available': False,
                'message': 'GitHub integration not configured'
            }
        
        return {
            'github_available': True,
            'has_repository': bool(project.github_repo_name),
            'repository_name': project.github_repo_name,
            'project_private': project.private
        }
    
    # ========== METODI HELPER PRIVATI ==========
    
    def _generate_repo_name(self, project: Project) -> str:
        """
        Genera un nome repository valido per GitHub basato sul progetto.
        
        Args:
            project: Progetto KICKTHISUSS
        
        Returns:
            Nome repository sanitized
        """
        # Usa il nome del progetto + ID per unicità
        base_name = f"{project.name}-{project.id}"
        return GitHubService._sanitize_repo_name(base_name)
    
    def _generate_repo_description(self, project: Project) -> str:
        """
        Genera descrizione repository da informazioni progetto.
        
        Args:
            project: Progetto KICKTHISUSS
        
        Returns:
            Descrizione repository
        """
        pitch = project.pitch or "No description provided"
        project_type = "🔬 Scientific Research" if project.is_scientific else "💡 Startup Project"
        return f"{project_type} | {pitch[:100]}... | Created via KICKTHISUSS platform"
    
    def _get_gitignore_template(self, project: Project) -> Optional[str]:
        """
        Determina il template .gitignore appropriato basato sul progetto.
        
        Args:
            project: Progetto KICKTHISUSS
        
        Returns:
            Nome template gitignore o None
        """
        category_map = {
            'Tech': 'Python',
            'Gaming': 'Unity',
            'Education': 'Python',
        }
        return category_map.get(project.category, None)
    
    def _create_initial_readme(self, project: Project, repo_name: str) -> bool:
        """
        Crea README.md iniziale con informazioni del progetto.
        
        Args:
            project: Progetto KICKTHISUSS
            repo_name: Nome del repository GitHub
        
        Returns:
            True se creato con successo, False altrimenti
        """
        try:
            readme_content = f"""# {project.name}

{project.pitch or 'No description provided'}

## About This Project

**Type:** {'🔬 Scientific Research' if project.is_scientific else '💡 Startup'}  
**Category:** {project.category}  
**Created:** {project.created_at.strftime('%Y-%m-%d') if project.created_at else 'Unknown'}

## Description

{project.description or 'No detailed description yet.'}

---

*This project is managed via [KICKTHISUSS](https://kickthisuss.com) platform.*  
*Repository automatically synchronized with project #{project.id}*

## Getting Started

This repository is synchronized with KICKTHISUSS. Contributors work through the KICKTHISUSS platform, and code is automatically synced here.

## Contributing

To contribute to this project, visit: [KICKTHISUSS Project Page](https://kickthisuss.com/projects/{project.id})

## License

Project license to be determined by project creator.
"""
            
            result = self.github_service.upload_file(
                repo_name=repo_name,
                file_path='README.md',
                content=readme_content.encode('utf-8'),
                commit_message='Initial README.md via KICKTHISUSS'
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to create README for project {project.id}: {e}")
            return False
    
    def submit_solution_zip(
        self,
        project: Project,
        task: Task,
        user: User,
        zip_path: str
    ) -> Dict[str, Any]:
        """
        Sottomette una soluzione via ZIP creando automaticamente una Pull Request.
        
        Flow:
        1. Crea un branch univoco (solution/task-{id}-{user})
        2. Estrae lo ZIP
        3. Carica i file sul branch
        4. Crea la PR verso il main branch
        
        Args:
            project: Progetto
            task: Task relativo alla soluzione
            user: Utente che sottomette
            zip_path: Path del file ZIP caricato
            
        Returns:
            Dict con risultati (pr_url, pr_number, etc.)
        """
        if not self.is_enabled():
            return {'success': False, 'error': 'GitHub sync disabled'}
            
        if not project.github_repo_name:
            return {'success': False, 'error': 'GitHub repository not configured'}
            
        try:
            # 1. Genera nome branch univoco
            safe_username = self._sanitize_repo_name(user.username)
            branch_name = f"solution/task-{task.id}-{safe_username}"
            
            # Crea il branch (se esiste già, potremmo volerlo aggiornare o fallire - qui proviamo a creare)
            # Se fallisce perché esiste, potremmo appendere un timestamp, ma per ora assumiamo un branch per task/user
            try:
                self.github_service.create_branch(
                    repo_name=project.github_repo_name,
                    branch_name=branch_name,
                    source_branch="main" # Assumiamo main come base
                )
            except GitHubServiceError as e:
                if "Reference already exists" in str(e):
                    logger.info(f"Branch {branch_name} already exists, updating it.")
                else:
                    raise
            
            # 2. Estrai ZIP e prepara file
            processor = ZipProcessor()
            temp_dir = None
            try:
                # Estrai in temp
                with open(zip_path, 'rb') as f:
                    extracted_files = processor.extract_zip(f)
                
                temp_dir = processor.temp_dir
                
                # Raccogli file per upload
                files_to_upload = []
                for root, dirs, files in os.walk(temp_dir):
                    # Filtra cartelle nascoste/inutili
                    dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', '.venv', 'node_modules'}]
                    
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(file_path, temp_dir).replace('\\', '/')
                        
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            
                        files_to_upload.append({
                            'path': rel_path,
                            'content': content
                        })
                
                if not files_to_upload:
                    return {'success': False, 'error': 'ZIP archive is empty or contains only ignored files'}
                
                # 3. Carica file sul branch (Batch Upload)
                commit_message = f"Solution for Task #{task.id}: {task.title}"
                
                upload_result = self.github_service.upload_files_batch(
                    repo_name=project.github_repo_name,
                    files=files_to_upload,
                    commit_message=commit_message,
                    branch=branch_name
                )
                
                if not upload_result:
                    raise Exception("Failed to upload files to GitHub")
                    
            finally:
                # Cleanup temp dir
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
            
            # 4. Crea Pull Request
            pr_title = f"Solution: {task.title} (Task #{task.id})"
            pr_body = f"""
## Solution for Task #{task.id}
**Task:** {task.title}
**Submitter:** @{user.username}

This PR was automatically created from a ZIP submission via KickThisUSS.
"""
            # Verifica se esiste già una PR aperta per questo branch
            # (Per ora proviamo a creare, se fallisce gestiamo l'errore o assumiamo che l'utente veda quella esistente)
            
            try:
                pr_result = self.github_service.create_pull_request(
                    repo_name=project.github_repo_name,
                    title=pr_title,
                    body=pr_body,
                    head=branch_name,
                    base="main"
                )
            except GitHubServiceError as e:
                if "A pull request already exists" in str(e):
                    # Recupera la PR esistente (TODO: implementare get_pulls in GitHubService se serve)
                    # Per ora ritorniamo successo parziale
                    logger.info("PR already exists for this branch")
                    return {
                        'success': True,
                        'branch': branch_name,
                        'message': 'Files updated on existing PR',
                        'pr_exists': True
                    }
                raise

            return {
                'success': True,
                'pr_number': pr_result['number'],
                'pr_url': pr_result['html_url'],
                'branch': branch_name,
                'commit_sha': upload_result['commit']['sha']
            }

        except Exception as e:
            logger.error(f"Failed to submit solution zip: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        """
        Sincronizza un intero workspace caricato via ZIP con UN SINGOLO COMMIT.
        Questo è il metodo "Smart Sync" che evita centinaia di commit individuali.
        
        Args:
            project: Progetto da sincronizzare
            zip_extract_path: Path assoluto dove è stato estratto lo ZIP
        
        Returns:
            Dict con risultati: {'status': str, 'message': str, 'commit_sha': str, 'files_synced': int}
        """
        from app.workspace_utils import should_sync_to_github, is_file_safe
        import base64
        
        if not self.is_enabled():
            return {'status': 'disabled', 'message': 'GitHub sync is disabled globally'}
        
        if not project.github_repo_name:
            return {'status': 'error', 'message': 'GitHub repository not configured'}
        
        logger.info(f"🔄 Starting Smart Sync for project {project.id} from {zip_extract_path}")
        
        # 1. Raccogli tutti i file da sincronizzare (con filtri)
        files_to_sync = []
        blocked_files = []
        ignored_files = []
        
        for root, dirs, files in os.walk(zip_extract_path):
            # Filtra cartelle blacklisted in-place
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.venv', 'venv', 'node_modules', '.git', 'dist', 'build'}]
            
            for filename in files:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, zip_extract_path).replace('\\', '/')
                
                # Security check
                is_safe, safety_reason = is_file_safe(relative_path)
                if not is_safe:
                    blocked_files.append(f"{relative_path} ({safety_reason})")
                    continue
                
                # Sync filter
                should_sync, sync_reason = should_sync_to_github(relative_path)
                if not should_sync:
                    ignored_files.append(f"{relative_path} ({sync_reason})")
                    continue
                
                # File OK, preparalo per sync
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    files_to_sync.append({
                        'path': f"workspace/{relative_path}",
                        'content': content
                    })
                except Exception as e:
                    logger.error(f"Error reading file {relative_path}: {e}")
        
        logger.info(
            f"📦 Smart Sync scan results: "
            f"{len(files_to_sync)} to sync, "
            f"{len(ignored_files)} ignored, "
            f"{len(blocked_files)} blocked"
        )
        
        if not files_to_sync:
            return {
                'status': 'info',
                'message': 'No files to sync (all filtered)',
                'files_synced': 0,
                'files_ignored': len(ignored_files),
                'files_blocked': len(blocked_files)
            }
        
        # 2. Crea UN SINGOLO COMMIT con tutti i file (Tree API)
        try:
            # Usa il metodo batch esistente
            batch_files = []
            for file_data in files_to_sync:
                batch_files.append({
                    'path': file_data['path'],
                    'content': file_data['content'],
                    'mode': '100644'
                })
            
            commit_message = f"Update workspace: {len(files_to_sync)} files via Kickstorm"
            
            batch_result = self.github_service.upload_files_batch(
                repo_name=project.github_repo_name,
                files=batch_files,
                commit_message=commit_message,
                branch='main'
            )
            
            if batch_result and batch_result.get('commit_sha'):
                logger.info(
                    f"✅ Smart Sync completed for project {project.id}: "
                    f"{len(files_to_sync)} files in commit {batch_result['commit_sha']}"
                )
                
                return {
                    'status': 'success',
                    'message': f'Workspace synchronized: {len(files_to_sync)} files in 1 commit',
                    'commit_sha': batch_result['commit_sha'],
                    'commit_url': f"https://github.com/{project.github_repo_name}/commit/{batch_result['commit_sha']}",
                    'files_synced': len(files_to_sync),
                    'files_ignored': len(ignored_files),
                    'files_blocked': len(blocked_files)
                }
            else:
                raise Exception("Batch upload returned no commit SHA")
        
        except Exception as e:
            logger.error(f"❌ Smart Sync failed for project {project.id}: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f'GitHub sync failed: {str(e)}',
                'files_synced': 0,
                'files_ignored': len(ignored_files),
                'files_blocked': len(blocked_files)
            }
    
    def __repr__(self):
        status = "enabled" if self.is_enabled() else "disabled"
        return f"<GitHubSyncService status={status}>"

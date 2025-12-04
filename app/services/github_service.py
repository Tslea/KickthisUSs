# app/services/github_service.py
"""
GitHub Integration Service
Gestisce tutte le interazioni con GitHub API in modo trasparente per l'utente.

DESIGN PRINCIPLES:
1. Fail gracefully - Se GitHub non funziona, l'app continua a funzionare
2. Zero visibility - L'utente NON vede mai GitHub
3. Async-ready - Pronto per operazioni in background
4. Security-first - Token e credenziali protetti
"""

import os
import base64
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from flask import current_app

# Import common utilities
from app.utils.github_utils import sanitize_repo_name, generate_pr_body

try:
    from github import Github, GithubException, RateLimitExceededException
    from github.Repository import Repository
    from github.GithubObject import NotSet
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    Github = None
    GithubException = Exception
    RateLimitExceededException = Exception
    Repository = None

logger = logging.getLogger(__name__)


class GitHubServiceError(Exception):
    """Custom exception for GitHub service errors"""
    pass


class GitHubService:
    """
    Service per interagire con GitHub API.
    Gli utenti NON vedono GitHub - tutto avviene dietro le quinte.
    """
    
    def __init__(self, token: Optional[str] = None, org: Optional[str] = None):
        """
        Inizializza il servizio GitHub.
        
        Args:
            token: GitHub Personal Access Token (se None, usa config)
            org: Nome organizzazione GitHub (se None, usa config)
        """
        if not GITHUB_AVAILABLE:
            logger.warning("PyGithub not installed - GitHub integration disabled")
            self.enabled = False
            return
        
        # Ottieni configurazione da Flask config o parametri
        self.token = token or current_app.config.get('GITHUB_TOKEN')
        self.org_name = org or current_app.config.get('GITHUB_ORG')
        self.enabled = current_app.config.get('GITHUB_ENABLED', False)
        self.default_private = current_app.config.get('GITHUB_DEFAULT_PRIVATE', True)
        
        if not self.enabled:
            logger.info("GitHub integration disabled in config")
            return
        
        if not self.token:
            logger.error("GitHub token not configured - integration will not work")
            self.enabled = False
            return
        
        try:
            self.github = Github(self.token)
            # Test connection
            self.user = self.github.get_user()
            logger.info(f"GitHub service initialized for user: {self.user.login}")
            
            # Ottieni organization se specificata
            if self.org_name:
                try:
                    self.org = self.github.get_organization(self.org_name)
                    logger.info(f"Using GitHub organization: {self.org_name}")
                except GithubException as e:
                    logger.warning(f"Could not access organization {self.org_name}: {e}")
                    self.org = None
            else:
                self.org = None
                
        except Exception as e:
            logger.error(f"Failed to initialize GitHub service: {e}")
            self.enabled = False
            self.github = None
    
    def is_enabled(self) -> bool:
        """Verifica se il servizio GitHub è abilitato e funzionante."""
        return self.enabled and self.github is not None
    
    def get_rate_limit(self) -> Dict[str, Any]:
        """
        Ottieni informazioni sul rate limit GitHub.
        
        Returns:
            Dict con informazioni su rate limit
        """
        if not self.is_enabled():
            return {'enabled': False}
        
        try:
            rate_limit = self.github.get_rate_limit()
            return {
                'enabled': True,
                'core': {
                    'limit': rate_limit.core.limit,
                    'remaining': rate_limit.core.remaining,
                    'reset': rate_limit.core.reset
                },
                'search': {
                    'limit': rate_limit.search.limit,
                    'remaining': rate_limit.search.remaining
                }
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit: {e}")
            return {'enabled': True, 'error': str(e)}
    
    def create_repository(
        self, 
        name: str, 
        description: Optional[str] = None,
        private: Optional[bool] = None,
        auto_init: bool = True,
        gitignore_template: Optional[str] = None,
        license_template: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Crea un nuovo repository GitHub.
        
        Args:
            name: Nome del repository
            description: Descrizione del progetto
            private: Se True, repository privato (default da config)
            auto_init: Se True, inizializza con README
            gitignore_template: Template .gitignore (es. 'Python', 'Node', 'Go')
            license_template: Template licenza (es. 'mit', 'apache-2.0')
        
        Returns:
            Dict con informazioni del repository creato o None se errore
        """
        if not self.is_enabled():
            logger.warning("GitHub service not enabled - cannot create repository")
            return None
        
        try:
            # Usa default se private non specificato
            is_private = private if private is not None else self.default_private
            
            # Sanitize repository name (GitHub requirements)
            repo_name = sanitize_repo_name(name)
            
            # Crea repository nell'organizzazione o account personale
            if self.org:
                repo = self.org.create_repo(
                    name=repo_name,
                    description=description or "Project created via KICKTHISUSS",
                    private=is_private,
                    auto_init=auto_init,
                    gitignore_template=gitignore_template or NotSet,
                    license_template=license_template or NotSet
                )
            else:
                repo = self.user.create_repo(
                    name=repo_name,
                    description=description or "Project created via KICKTHISUSS",
                    private=is_private,
                    auto_init=auto_init,
                    gitignore_template=gitignore_template or NotSet,
                    license_template=license_template or NotSet
                )
            
            logger.info(f"Created GitHub repository: {repo.full_name}")
            
            return {
                'id': repo.id,
                'name': repo.name,
                'full_name': repo.full_name,
                'html_url': repo.html_url,
                'clone_url': repo.clone_url,
                'ssh_url': repo.ssh_url,
                'private': repo.private,
                'created_at': repo.created_at.isoformat() if repo.created_at else None
            }
            
        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded")
            raise GitHubServiceError("Rate limit exceeded. Please try again later.")
        except GithubException as e:
            logger.error(f"GitHub API error creating repository: {e}")
            raise GitHubServiceError(f"Failed to create repository: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"Unexpected error creating repository: {e}")
            raise GitHubServiceError(f"Unexpected error: {str(e)}")
    
    def get_repository(self, repo_name: str) -> Optional[Repository]:
        """
        Ottieni un repository esistente.
        
        Args:
            repo_name: Nome del repository (solo nome o full_name)
        
        Returns:
            Repository object o None se non trovato
        """
        if not self.is_enabled():
            return None
        
        try:
            # Se è un nome completo (org/repo)
            if '/' in repo_name:
                full_name = repo_name
            # Altrimenti costruisci il full name
            elif self.org:
                full_name = f"{self.org_name}/{repo_name}"
            else:
                full_name = f"{self.user.login}/{repo_name}"
            
            repo = self.github.get_repo(full_name)
            logger.info(f"Retrieved repository: {repo.full_name}")
            return repo
            
        except GithubException as e:
            logger.warning(f"Repository not found: {repo_name} - {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting repository: {e}")
            return None
    
    def upload_files_batch(
        self,
        repo_name: str,
        files: List[Dict[str, Any]],
        commit_message: str = "Batch upload via KickthisUSs",
        branch: str = "main"
    ) -> Optional[Dict[str, Any]]:
        """
        Carica multipli file su GitHub usando Tree API (batch upload).
        Molto più veloce di upload sequenziali (10-30x).
        
        Args:
            repo_name: Nome repository (es. "org/repo")
            files: Lista di dict con keys: 'path', 'content' (bytes), 'mode' (opzionale, default '100644')
            commit_message: Messaggio commit
            branch: Branch su cui committare
        
        Returns:
            Dict con info del commit creato o None se errore
        """
        if not self.is_enabled():
            logger.warning("GitHub service not enabled - cannot upload files batch")
            return None
        
        if not files:
            logger.warning("Empty files list for batch upload")
            return None
        
        start_time = datetime.utcnow()
        total_size = sum(len(f.get('content', b'')) if isinstance(f.get('content'), bytes) else 0 for f in files)
        
        try:
            repo = self.get_repository(repo_name)
            if not repo:
                raise GitHubServiceError(f"Repository {repo_name} not found")
            
            # Valida dimensione file (GitHub limite 100MB per file)
            MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
            for file_info in files:
                content = file_info.get('content', b'')
                if isinstance(content, str):
                    content = content.encode('utf-8')
                if len(content) > MAX_FILE_SIZE:
                    raise GitHubServiceError(f"File {file_info.get('path')} exceeds 100MB limit ({len(content)} bytes)")
            
            # Ottieni branch e commit corrente
            try:
                branch_ref = repo.get_branch(branch)
                base_commit_sha = branch_ref.commit.sha
            except GithubException:
                # Branch non esiste - crealo da default branch o fallback
                try:
                    default_branch = repo.default_branch
                    branch_ref = repo.get_branch(default_branch)
                    base_commit_sha = branch_ref.commit.sha
                    # Crea nuovo branch se necessario
                    repo.create_git_ref(ref=f"refs/heads/{branch}", sha=base_commit_sha)
                    logger.info(f"Created branch {branch} from {default_branch}")
                except GithubException as e:
                    raise GitHubServiceError(f"Could not get base commit for branch {branch}: {e}")
            
            # Ottieni tree corrente (recursive per vedere tutti i file)
            base_commit = repo.get_git_commit(base_commit_sha)
            base_tree_sha = base_commit.tree.sha
            
            # Costruisci mappa path -> SHA per file esistenti
            existing_files = {}
            try:
                base_tree = repo.get_git_tree(base_tree_sha, recursive=True)
                for item in base_tree.tree:
                    if item.type == 'blob':  # Solo file, non directory
                        existing_files[item.path] = item.sha
            except GithubException as e:
                logger.warning(f"Could not get recursive tree (might be empty repo): {e}")
                existing_files = {}
            
            # Crea blob per nuovi file o usa SHA esistenti
            tree_items = []
            new_files_count = 0
            updated_files_count = 0
            
            for file_info in files:
                file_path = file_info.get('path')
                content = file_info.get('content', b'')
                mode = file_info.get('mode', '100644')  # Default: file normale
                
                if isinstance(content, str):
                    content = content.encode('utf-8')
                
                # Se file esiste e contenuto è identico, usa SHA esistente
                if file_path in existing_files:
                    # Verifica se contenuto è cambiato (opzionale: potremmo sempre creare nuovo blob)
                    # Per semplicità, creiamo sempre nuovo blob se file è nella lista upload
                    blob_sha = existing_files[file_path]
                    updated_files_count += 1
                else:
                    blob_sha = None
                    new_files_count += 1
                
                # Crea nuovo blob (anche per file esistenti, per garantire contenuto aggiornato)
                content_base64 = base64.b64encode(content).decode('utf-8')
                blob = repo.create_git_blob(content_base64, 'base64')
                blob_sha = blob.sha
                
                tree_items.append({
                    'path': file_path,
                    'mode': mode,
                    'type': 'blob',
                    'sha': blob_sha
                })
            
            # Crea nuovo tree
            # base_tree mantiene automaticamente tutti i file esistenti non modificati
            # tree_items contiene solo i file nuovi/aggiornati
            new_tree = repo.create_git_tree(tree_items, base_tree=base_tree_sha)
            
            # Crea commit
            new_commit = repo.create_git_commit(
                message=commit_message,
                tree=new_tree.sha,
                parents=[base_commit_sha]
            )
            
            # Aggiorna branch
            branch_ref_obj = repo.get_git_ref(f"refs/heads/{branch}")
            branch_ref_obj.edit(new_commit.sha)
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Batch upload successful: {len(files)} files ({new_files_count} new, {updated_files_count} updated) "
                f"in {elapsed:.2f}s ({total_size / 1024 / 1024:.2f} MB total)"
            )
            
            return {
                'commit': {
                    'sha': new_commit.sha,
                    'url': new_commit.html_url if hasattr(new_commit, 'html_url') else None,
                    'message': commit_message
                },
                'tree': {
                    'sha': new_tree.sha
                },
                'files_count': len(files),
                'new_files': new_files_count,
                'updated_files': updated_files_count,
                'elapsed_seconds': elapsed,
                'total_size_bytes': total_size
            }
            
        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded during batch upload")
            raise GitHubServiceError("Rate limit exceeded. Please try again later.")
        except GithubException as e:
            logger.error(f"GitHub API error during batch upload: {e}")
            raise GitHubServiceError(f"Failed to batch upload files: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"Unexpected error during batch upload: {e}", exc_info=True)
            raise GitHubServiceError(f"Unexpected error: {str(e)}")
    
    def upload_file(
        self,
        repo_name: str,
        file_path: str,
        content: bytes,
        commit_message: Optional[str] = None,
        branch: str = "main"
    ) -> Optional[Dict[str, Any]]:
        """
        Carica un file su GitHub repository.
        
        Args:
            repo_name: Nome del repository
            file_path: Percorso del file nel repository (es. 'src/main.py')
            content: Contenuto del file come bytes
            commit_message: Messaggio di commit (se None, auto-generato)
            branch: Nome del branch (default: main)
        
        Returns:
            Dict con informazioni del file caricato o None se errore
        """
        if not self.is_enabled():
            logger.warning("GitHub service not enabled - cannot upload file")
            return None
        
        try:
            repo = self.get_repository(repo_name)
            if not repo:
                raise GitHubServiceError(f"Repository {repo_name} not found")
            
            # Encode content to base64
            if isinstance(content, str):
                content = content.encode('utf-8')
            content_base64 = base64.b64encode(content).decode('utf-8')
            
            # Auto-generate commit message if not provided
            if not commit_message:
                timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                commit_message = f"Upload {os.path.basename(file_path)} via KICKTHISUSS ({timestamp})"
            
            # Check if file already exists (for update vs create)
            try:
                existing_file = repo.get_contents(file_path, ref=branch)
                # File exists - update it
                result = repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=content_base64,
                    sha=existing_file.sha,
                    branch=branch
                )
                action = "updated"
            except GithubException:
                # File doesn't exist - create it
                result = repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=content_base64,
                    branch=branch
                )
                action = "created"
            
            logger.info(f"File {action}: {file_path} in {repo.full_name}")
            
            return {
                'action': action,
                'path': file_path,
                'html_url': result['content'].html_url,
                'download_url': result['content'].download_url,
                'sha': result['content'].sha,
                'commit': {
                    'sha': result['commit'].sha,
                    'url': result['commit'].html_url
                }
            }
            
        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded")
            raise GitHubServiceError("Rate limit exceeded. Please try again later.")
        except GithubException as e:
            logger.error(f"GitHub API error uploading file: {e}")
            raise GitHubServiceError(f"Failed to upload file: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            raise GitHubServiceError(f"Unexpected error: {str(e)}")
    
    def create_issue(
        self,
        repo_name: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Crea un issue GitHub (equivalente a Task su KICKTHISUSS).
        
        Args:
            repo_name: Nome del repository
            title: Titolo dell'issue
            body: Descrizione dell'issue
            labels: Lista di label da applicare
            assignees: Lista di username da assegnare
        
        Returns:
            Dict con informazioni dell'issue creato o None se errore
        """
        if not self.is_enabled():
            logger.warning("GitHub service not enabled - cannot create issue")
            return None
        
        try:
            repo = self.get_repository(repo_name)
            if not repo:
                raise GitHubServiceError(f"Repository {repo_name} not found")
            
            issue = repo.create_issue(
                title=title,
                body=body or "Issue created via KICKTHISUSS platform",
                labels=labels or [],
                assignees=assignees or []
            )
            
            logger.info(f"Created issue #{issue.number} in {repo.full_name}")
            
            return {
                'number': issue.number,
                'title': issue.title,
                'html_url': issue.html_url,
                'state': issue.state,
                'created_at': issue.created_at.isoformat() if issue.created_at else None
            }
            
        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded")
            raise GitHubServiceError("Rate limit exceeded. Please try again later.")
        except GithubException as e:
            logger.error(f"GitHub API error creating issue: {e}")
            raise GitHubServiceError(f"Failed to create issue: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"Unexpected error creating issue: {e}")
            raise GitHubServiceError(f"Unexpected error: {str(e)}")
    
    def delete_repository(self, repo_name: str) -> bool:
        """
        Elimina un repository GitHub.
        ⚠️ OPERAZIONE PERICOLOSA - Usa con cautela!
        
        Args:
            repo_name: Nome del repository da eliminare
        
        Returns:
            True se eliminato con successo, False altrimenti
        """
        if not self.is_enabled():
            logger.warning("GitHub service not enabled - cannot delete repository")
            return False
        
        try:
            repo = self.get_repository(repo_name)
            if not repo:
                logger.warning(f"Repository {repo_name} not found - cannot delete")
                return False
            
            repo.delete()
            logger.warning(f"⚠️ Deleted GitHub repository: {repo_name}")
            return True
            
        except GithubException as e:
            logger.error(f"GitHub API error deleting repository: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting repository: {e}")
            return False
    

    
    def sync_task_to_github(self, task, project) -> bool:
        """
        Sincronizza un task con GitHub Issue (crea o aggiorna).
        Funzione invisibile all'utente - funziona automaticamente.
        
        Args:
            task: Task object da sincronizzare
            project: Project object associato
        
        Returns:
            True se sincronizzazione riuscita, False altrimenti
        """
        if not self.is_enabled():
            logger.debug("GitHub service not enabled - skipping task sync")
            return False
        
        if not project.github_repo_name:
            logger.debug(f"Project {project.id} has no GitHub repository - skipping sync")
            return False
        
        try:
            # Prepara il body dell'issue
            body_parts = []
            
            if task.description:
                body_parts.append(f"**Descrizione:**\n{task.description}")
            
            if task.equity_reward and task.equity_reward > 0:
                body_parts.append(f"\n**Equity Reward:** {task.equity_reward}%")
            
            if task.difficulty:
                body_parts.append(f"\n**Difficoltà:** {task.difficulty}")
            
            # Estimated hours field removed - not in Task model
            
            body_parts.append(f"\n\n---\n*Sincronizzato automaticamente da KickThisUSS*")
            body = "\n".join(body_parts)
            
            # Prepara labels
            labels = []
            if task.difficulty:
                labels.append(f"difficulty:{task.difficulty}")
            if task.status:
                labels.append(f"status:{task.status}")
            
            # Se il task ha già un issue number, aggiorna
            if task.github_issue_number:
                result = self.update_issue(
                    repo_name=project.github_repo_name,
                    issue_number=task.github_issue_number,
                    title=task.title,
                    body=body,
                    labels=labels,
                    state='closed' if task.status == 'completed' else 'open'
                )
            else:
                # Altrimenti crea nuovo issue
                result = self.create_issue(
                    repo_name=project.github_repo_name,
                    title=task.title,
                    body=body,
                    labels=labels
                )
                
                if result:
                    # Salva issue number nel task
                    task.github_issue_number = result['number']
            
            if result:
                task.github_synced_at = datetime.utcnow()
                logger.info(f"Task {task.id} synced to GitHub issue #{task.github_issue_number}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to sync task {task.id} to GitHub: {e}")
            return False
    
    def update_issue(
        self,
        repo_name: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        state: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Aggiorna un issue GitHub esistente.
        
        Args:
            repo_name: Nome del repository
            issue_number: Numero dell'issue da aggiornare
            title: Nuovo titolo (opzionale)
            body: Nuovo body (opzionale)
            labels: Nuove labels (opzionale)
            state: Nuovo stato 'open' o 'closed' (opzionale)
        
        Returns:
            Dict con informazioni dell'issue aggiornato o None se errore
        """
        if not self.is_enabled():
            logger.warning("GitHub service not enabled - cannot update issue")
            return None
        
        try:
            repo = self.get_repository(repo_name)
            if not repo:
                raise GitHubServiceError(f"Repository {repo_name} not found")
            
            issue = repo.get_issue(issue_number)
            
            # Prepara i parametri da aggiornare
            update_params = {}
            if title is not None:
                update_params['title'] = title
            if body is not None:
                update_params['body'] = body
            if labels is not None:
                update_params['labels'] = labels
            if state is not None:
                update_params['state'] = state
            
            issue.edit(**update_params)
            
            logger.info(f"Updated issue #{issue_number} in {repo.full_name}")
            
            return {
                'number': issue.number,
                'title': issue.title,
                'html_url': issue.html_url,
                'state': issue.state,
                'updated_at': issue.updated_at.isoformat() if issue.updated_at else None
            }
            
        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded")
            raise GitHubServiceError("Rate limit exceeded. Please try again later.")
        except GithubException as e:
            logger.error(f"GitHub API error updating issue: {e}")
            raise GitHubServiceError(f"Failed to update issue: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"Unexpected error updating issue: {e}")
            raise GitHubServiceError(f"Unexpected error: {str(e)}")
    
    def create_branch(
        self,
        repo_name: str,
        branch_name: str,
        source_branch: str = "main"
    ) -> Optional[Dict[str, Any]]:
        """
        Crea un nuovo branch nel repository.
        
        Args:
            repo_name: Nome del repository
            branch_name: Nome del nuovo branch
            source_branch: Branch da cui partire (default: main)
            
        Returns:
            Dict con informazioni del branch creato o None se errore
        """
        if not self.is_enabled():
            logger.warning("GitHub service not enabled - cannot create branch")
            return None
            
        try:
            repo = self.get_repository(repo_name)
            if not repo:
                raise GitHubServiceError(f"Repository {repo_name} not found")
            
            # Ottieni SHA del source branch
            try:
                source_ref = repo.get_git_ref(f"heads/{source_branch}")
                sha = source_ref.object.sha
            except GithubException:
                # Se main non esiste, prova master
                if source_branch == "main":
                    try:
                        source_ref = repo.get_git_ref("heads/master")
                        sha = source_ref.object.sha
                    except GithubException:
                         # Se neanche master esiste, prova default branch
                        default_branch = repo.default_branch
                        source_ref = repo.get_git_ref(f"heads/{default_branch}")
                        sha = source_ref.object.sha
                else:
                    raise
            
            # Crea il nuovo ref
            ref = repo.create_git_ref(f"refs/heads/{branch_name}", sha)
            
            logger.info(f"Created branch {branch_name} in {repo.full_name}")
            
            return {
                'name': branch_name,
                'sha': sha,
                'url': f"{repo.html_url}/tree/{branch_name}"
            }
            
        except GithubException as e:
            logger.error(f"GitHub API error creating branch: {e}")
            raise GitHubServiceError(f"Failed to create branch: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"Unexpected error creating branch: {e}")
            raise GitHubServiceError(f"Unexpected error: {str(e)}")

    def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> Optional[Dict[str, Any]]:
        """
        Crea una Pull Request.
        
        Args:
            repo_name: Nome del repository
            title: Titolo della PR
            body: Descrizione della PR
            head: Branch con le modifiche (es. 'feature-branch')
            base: Branch di destinazione (es. 'main')
            
        Returns:
            Dict con informazioni della PR creata o None se errore
        """
        if not self.is_enabled():
            logger.warning("GitHub service not enabled - cannot create PR")
            return None
            
        try:
            repo = self.get_repository(repo_name)
            if not repo:
                raise GitHubServiceError(f"Repository {repo_name} not found")
            
            # Verifica se il base branch esiste, altrimenti usa default
            try:
                repo.get_branch(base)
            except GithubException:
                base = repo.default_branch
            
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base
            )
            
            logger.info(f"Created PR #{pr.number} in {repo.full_name}")
            
            return {
                'number': pr.number,
                'title': pr.title,
                'html_url': pr.html_url,
                'state': pr.state,
                'created_at': pr.created_at.isoformat() if pr.created_at else None,
                'head': head,
                'base': base
            }
            
        except GithubException as e:
            logger.error(f"GitHub API error creating PR: {e}")
            raise GitHubServiceError(f"Failed to create PR: {e.data.get('message', str(e))}")
        except Exception as e:
            logger.error(f"Unexpected error creating PR: {e}")
            raise GitHubServiceError(f"Unexpected error: {str(e)}")

    def get_repo_stats(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """
        Ottieni statistiche del repository GitHub.
        
        Returns:
            Dict con statistiche o None se errore
        """
        if not self.is_enabled():
            return None
        
        try:
            repo = self.get_repository(repo_name)
            if not repo:
                return None
            
            # Conta issues aperti e chiusi
            open_issues = repo.open_issues_count
            closed_issues = repo.get_issues(state='closed').totalCount
            
            # Conta commits recenti (ultimi 30 giorni)
            from datetime import datetime, timedelta
            since_date = datetime.utcnow() - timedelta(days=30)
            recent_commits = repo.get_commits(since=since_date).totalCount
            
            # Ottieni contributors
            contributors_count = repo.get_contributors().totalCount
            
            # Ottieni data ultimo aggiornamento
            updated_at = repo.updated_at
            
            return {
                'open_issues': open_issues,
                'closed_issues': closed_issues,
                'total_issues': open_issues + closed_issues,
                'recent_commits': recent_commits,
                'contributors': contributors_count,
                'updated_at': updated_at.isoformat() if updated_at else None,
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'watchers': repo.watchers_count
            }
            
        except Exception as e:
            logger.error(f"Error getting repo stats for {repo_name}: {e}")
            return None
    
    def create_pr_from_zip(
        self,
        project: Any,
        solution: Any,
        zip_files: List[Dict[str, Any]],
        user_info: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Crea una Pull Request da file ZIP estratti.
        
        Args:
            project: Oggetto Project con github_repo_name
            solution: Oggetto Solution appena creato (ha .id)
            zip_files: Lista di dict {path, content, size, type} da ZipProcessor
            user_info: Dict con {username, email, github_username}
        
        Returns:
            Dict {success: bool, pr_url: str, pr_number: int, branch: str, commit_sha: str, error: str}
        """
        if not self.is_enabled():
            return {'success': False, 'error': 'GitHub integration not enabled'}
        
        if not project.github_repo_name:
            return {'success': False, 'error': 'Project has no GitHub repository configured'}
        
        try:
            # Ottieni repository
            repo = self.get_repository(project.github_repo_name)
            if not repo:
                return {'success': False, 'error': f'Repository {project.github_repo_name} not found'}
            
            # Crea branch name
            username_safe = user_info['username'].replace(' ', '-').replace('_', '-').lower()
            branch_name = f"solution-{solution.id}-{username_safe}"
            
            # Ottieni branch base (default: main o master)
            try:
                base_branch = repo.default_branch
                base_ref = repo.get_branch(base_branch)
                base_sha = base_ref.commit.sha
            except GithubException:
                # Fallback a "main"
                try:
                    base_ref = repo.get_branch("main")
                    base_sha = base_ref.commit.sha
                    base_branch = "main"
                except GithubException:
                    # Fallback a "master"
                    try:
                        base_ref = repo.get_branch("master")
                        base_sha = base_ref.commit.sha
                        base_branch = "master"
                    except GithubException:
                        return {'success': False, 'error': 'No base branch found (main/master)'}
            
            # Crea nuovo branch
            try:
                repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
                logger.info(f"Created branch {branch_name} from {base_branch}")
            except GithubException as e:
                if 'Reference already exists' in str(e):
                    # Branch già esistente - aggiorna con timestamp
                    branch_name = f"{branch_name}-{int(datetime.now().timestamp())}"
                    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)
                else:
                    raise
            
            # Commit file-by-file
            commit_messages = []
            files_committed = 0
            last_commit_sha = base_sha
            
            for file_info in zip_files:
                # Skip binary files troppo grandi (>1MB)
                if file_info['type'] == 'binary' and file_info['size'] > 1048576:
                    logger.warning(f"Skipping large binary file: {file_info['path']} ({file_info['size']} bytes)")
                    continue
                
                file_path = file_info['path']
                
                # Prepara contenuto
                if file_info['type'] == 'text' and file_info['content']:
                    content = file_info['content']
                else:
                    # Leggi file binary
                    try:
                        with open(file_info['full_path'], 'rb') as f:
                            content = f.read()
                    except Exception as e:
                        logger.warning(f"Could not read file {file_path}: {e}")
                        continue
                
                # Commit singolo file
                try:
                    # Verifica se file esiste nel branch
                    file_exists = False
                    try:
                        existing_file = repo.get_contents(file_path, ref=branch_name)
                        file_exists = True
                    except:
                        pass
                    
                    commit_message = f"Add {file_path}" if not file_exists else f"Update {file_path}"
                    
                    if file_exists:
                        # Update file esistente
                        repo.update_file(
                            path=file_path,
                            message=commit_message,
                            content=content,
                            sha=existing_file.sha,
                            branch=branch_name
                        )
                    else:
                        # Create nuovo file
                        repo.create_file(
                            path=file_path,
                            message=commit_message,
                            content=content,
                            branch=branch_name
                        )
                    
                    commit_messages.append(commit_message)
                    files_committed += 1
                    
                except GithubException as e:
                    logger.warning(f"Failed to commit {file_path}: {e}")
                    continue
            
            if files_committed == 0:
                return {'success': False, 'error': 'No files were committed'}
            
            # Ottieni ultimo commit del branch
            branch_ref = repo.get_branch(branch_name)
            last_commit_sha = branch_ref.commit.sha
            
            # Crea Pull Request
            pr_title = f"Solution for Task #{solution.task_id} by {user_info['username']}"
            # Generate PR body using common utility
            pr_body = generate_pr_body(solution, user_info, files_committed, commit_messages)
            
            pr = repo.create_pull(
                title=pr_title,
                body=pr_body,
                head=branch_name,
                base=base_branch
            )
            
            logger.info(f"Created PR #{pr.number}: {pr.html_url}")
            
            return {
                'success': True,
                'pr_url': pr.html_url,
                'pr_number': pr.number,
                'branch': branch_name,
                'commit_sha': last_commit_sha,
                'files_committed': files_committed
            }
            
        except RateLimitExceededException:
            logger.error("GitHub API rate limit exceeded")
            return {'success': False, 'error': 'Rate limit exceeded. Please try again later.'}
        except GithubException as e:
            logger.error(f"GitHub API error creating PR: {e}")
            return {'success': False, 'error': f'GitHub error: {e.data.get("message", str(e))}'}
        except Exception as e:
            logger.error(f"Unexpected error creating PR from ZIP: {e}", exc_info=True)
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}
    

    
    def __repr__(self):
        status = "enabled" if self.is_enabled() else "disabled"
        org_info = f", org={self.org_name}" if self.org_name else ""
        return f"<GitHubService status={status}{org_info}>"


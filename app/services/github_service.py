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
            repo_name = self._sanitize_repo_name(name)
            
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
    
    @staticmethod
    def _sanitize_repo_name(name: str) -> str:
        """
        Sanitize repository name per GitHub requirements.
        - Lowercase
        - Replace spaces and special chars with hyphens
        - Remove consecutive hyphens
        - Max 100 characters
        
        Args:
            name: Nome originale del progetto
        
        Returns:
            Nome sanitized valido per GitHub
        """
        import re
        
        # Lowercase
        sanitized = name.lower()
        
        # Replace spaces and special chars with hyphens
        sanitized = re.sub(r'[^a-z0-9-_.]', '-', sanitized)
        
        # Remove consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        
        # Max 100 characters
        sanitized = sanitized[:100]
        
        # Ensure not empty
        if not sanitized:
            sanitized = f"project-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        return sanitized
    
    def __repr__(self):
        status = "enabled" if self.is_enabled() else "disabled"
        org_info = f", org={self.org_name}" if self.org_name else ""
        return f"<GitHubService status={status}{org_info}>"

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
from app.models import Project, db

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
        
        Args:
            project: Progetto a cui appartengono i file
            files: Lista di dict con keys: 'path', 'content', 'message' (opzionale)
        
        Returns:
            Dict con risultati: {'success': int, 'failed': int, 'errors': List[str]}
        """
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        if not self.is_enabled():
            results['errors'].append("GitHub sync is disabled globally")
            return results
        
        for file_info in files:
            file_path = file_info.get('path')
            content = file_info.get('content')
            message = file_info.get('message')
            
            if not file_path or content is None:
                results['failed'] += 1
                results['errors'].append(f"Invalid file info: {file_info}")
                continue
            
            success = self.sync_file(project, file_path, content, message)
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"Failed to sync: {file_path}")
        
        return results
    
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
    
    def __repr__(self):
        status = "enabled" if self.is_enabled() else "disabled"
        return f"<GitHubSyncService status={status}>"

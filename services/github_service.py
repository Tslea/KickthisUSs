"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Please use app.services.github_service.GitHubService instead.

This legacy service uses the requests library directly instead of PyGithub.
It is maintained only for backward compatibility with existing scripts.
"""
import warnings
import requests
import json
import base64
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from utils.github_config_loader import (
    GITHUB_TOKEN, GITHUB_ORG, GITHUB_API_BASE,
    GITHUB_TIMEOUT, GITHUB_MAX_RETRIES, GITHUB_RETRY_DELAY,
    PROJECT_STRUCTURE, REPO_TEMPLATE, SUPPORTED_FILE_FORMATS,
    get_content_type_from_extension, FILE_SIZE_LIMITS
)

# Import common utilities
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.utils.github_utils import sanitize_repo_name, generate_simple_pr_body

logger = logging.getLogger(__name__)

# Deprecation warning
warnings.warn(
    "services.github_service is deprecated. Use app.services.github_service instead.",
    DeprecationWarning,
    stacklevel=2
)


class GitHubService:
    """Servizio per gestire l'integrazione con GitHub in modo invisibile"""
    
    def __init__(self):
        self.token = GITHUB_TOKEN
        self.org = GITHUB_ORG
        self.api_base = GITHUB_API_BASE
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """Wrapper per richieste con retry logic"""
        kwargs.setdefault('timeout', GITHUB_TIMEOUT)
        kwargs.setdefault('headers', self.headers)
        
        for attempt in range(GITHUB_MAX_RETRIES):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"GitHub request failed (attempt {attempt + 1}/{GITHUB_MAX_RETRIES}): {e}")
                if attempt < GITHUB_MAX_RETRIES - 1:
                    time.sleep(GITHUB_RETRY_DELAY)
                else:
                    logger.error(f"GitHub request failed after {GITHUB_MAX_RETRIES} attempts")
                    return None
        return None
    
    def create_project_repo(self, project_id: int, project_data: Dict) -> Optional[str]:
        """
        Crea repository GitHub per un progetto
        Returns: URL del repository o None se fallisce
        """
        try:
            repo_name = f"project-{project_id}-{sanitize_repo_name(project_data.get('title', 'untitled'))}"
            
            # Payload per creazione repo
            payload = {
                'name': repo_name,
                'description': project_data.get('description', '')[:100],
                'private': False,
                'auto_init': True,
                'has_issues': True,
                'has_projects': True,
                'has_wiki': False
            }
            
            # Crea repo nell'organizzazione
            url = f"{self.api_base}/orgs/{self.org}/repos"
            response = self._make_request('POST', url, json=payload)
            
            if response:
                repo_url = response.json().get('html_url')
                logger.info(f"Repository created: {repo_url}")
                
                # Crea struttura directory base
                self._create_project_structure(repo_name, project_data.get('project_type', 'software'))
                
                return repo_url
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create repo for project {project_id}: {e}")
            return None
    
    def _create_project_structure(self, repo_name: str, project_type: str):
        """Crea struttura directory iniziale nel repository"""
        try:
            structure = PROJECT_STRUCTURE.get(project_type, PROJECT_STRUCTURE['software'])
            
            for folder, description in structure.items():
                # Crea file .gitkeep per mantenere la directory
                content = f"# {description}\n\nThis folder contains {description.lower()}."
                self._create_file(
                    repo_name,
                    f"{folder}/README.md",
                    content,
                    f"Initialize {folder} directory"
                )
            
            logger.info(f"Project structure created for {repo_name}")
        except Exception as e:
            logger.warning(f"Failed to create project structure: {e}")
    
    def create_solution_branch(self, project_id: int, solution_id: int, solution_data: Dict) -> Optional[str]:
        """
        Crea branch per una soluzione
        Returns: Nome del branch o None
        """
        try:
            repo_name = f"project-{project_id}"
            branch_name = f"solution-{solution_id}-{sanitize_repo_name(solution_data.get('title', 'solution'))}"
            
            # Ottieni SHA del branch main
            url = f"{self.api_base}/repos/{self.org}/{repo_name}/git/refs/heads/main"
            response = self._make_request('GET', url)
            
            if not response:
                return None
            
            main_sha = response.json()['object']['sha']
            
            # Crea nuovo branch
            payload = {
                'ref': f'refs/heads/{branch_name}',
                'sha': main_sha
            }
            
            url = f"{self.api_base}/repos/{self.org}/{repo_name}/git/refs"
            response = self._make_request('POST', url, json=payload)
            
            if response:
                logger.info(f"Branch created: {branch_name}")
                return branch_name
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create branch for solution {solution_id}: {e}")
            return None
    
    def upload_solution_files(self, repo_name: str, branch: str, files: List[Dict], base_path: str = ''):
        """
        Carica file di una soluzione nel repository
        files: Lista di dict con keys 'name', 'content', 'path'
        """
        try:
            for file_data in files:
                file_path = f"{base_path}/{file_data['path']}" if base_path else file_data['path']
                
                self._create_file(
                    repo_name,
                    file_path,
                    file_data['content'],
                    f"Add {file_data['name']}",
                    branch
                )
            
            logger.info(f"Uploaded {len(files)} files to {repo_name}/{branch}")
            
        except Exception as e:
            logger.error(f"Failed to upload files: {e}")
    
    def _create_file(self, repo_name: str, path: str, content: str, message: str, branch: str = 'main'):
        """Crea un file nel repository"""
        try:
            # Encode content in base64
            content_encoded = base64.b64encode(content.encode()).decode()
            
            payload = {
                'message': message,
                'content': content_encoded,
                'branch': branch
            }
            
            url = f"{self.api_base}/repos/{self.org}/{repo_name}/contents/{path}"
            response = self._make_request('PUT', url, json=payload)
            
            return response is not None
            
        except Exception as e:
            logger.error(f"Failed to create file {path}: {e}")
            return False
    
    def create_pull_request(self, repo_name: str, head_branch: str, solution_data: Dict) -> Optional[str]:
        """
        Crea pull request per una soluzione
        Returns: URL della PR o None
        """
        try:
            payload = {
                'title': f"Solution: {solution_data.get('title', 'New Solution')}",
                'body': generate_simple_pr_body(solution_data),
                'head': head_branch,
                'base': 'main'
            }
            
            url = f"{self.api_base}/repos/{self.org}/{repo_name}/pulls"
            response = self._make_request('POST', url, json=payload)
            
            if response:
                pr_url = response.json().get('html_url')
                pr_number = response.json().get('number')
                logger.info(f"Pull request created: {pr_url}")
                
                # Aggiungi labels
                self._add_pr_labels(repo_name, pr_number, solution_data.get('category', []))
                
                return pr_url
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to create pull request: {e}")
            return None
    
    # Removed: Now using common utility from app.utils.github_utils.generate_simple_pr_body
    
    def _add_pr_labels(self, repo_name: str, pr_number: int, categories: List[str]):
        """Aggiunge labels alla PR"""
        try:
            labels = ['solution'] + categories
            url = f"{self.api_base}/repos/{self.org}/{repo_name}/issues/{pr_number}/labels"
            self._make_request('POST', url, json={'labels': labels})
        except Exception as e:
            logger.warning(f"Failed to add labels: {e}")
    
    def list_repo_files(self, repo_name: str, path: str = '', branch: str = 'main') -> List[Dict]:
        """Lista file in un repository"""
        try:
            url = f"{self.api_base}/repos/{self.org}/{repo_name}/contents/{path}"
            params = {'ref': branch}
            response = self._make_request('GET', url, params=params)
            
            if response:
                return response.json()
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def get_file_content(self, repo_name: str, path: str, branch: str = 'main') -> Optional[str]:
        """Ottiene contenuto di un file"""
        try:
            url = f"{self.api_base}/repos/{self.org}/{repo_name}/contents/{path}"
            params = {'ref': branch}
            response = self._make_request('GET', url, params=params)
            
            if response:
                content_encoded = response.json().get('content', '')
                return base64.b64decode(content_encoded).decode()
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get file content: {e}")
            return None
    
    def sync_comments(self, repo_name: str, pr_number: int) -> List[Dict]:
        """Sincronizza commenti da GitHub PR"""
        try:
            url = f"{self.api_base}/repos/{self.org}/{repo_name}/issues/{pr_number}/comments"
            response = self._make_request('GET', url)
            
            if response:
                return response.json()
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to sync comments: {e}")
            return []
    
    def add_comment(self, repo_name: str, pr_number: int, comment_body: str) -> bool:
        """Aggiunge commento a una PR"""
        try:
            url = f"{self.api_base}/repos/{self.org}/{repo_name}/issues/{pr_number}/comments"
            payload = {'body': comment_body}
            response = self._make_request('POST', url, json=payload)
            
            return response is not None
            
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            return False
    
    def generate_preview(self, solution_data: Dict, files: List[Dict]) -> Dict:
        """Genera preview per visualizzazione soluzione"""
        preview = {
            'type': solution_data.get('type', 'unknown'),
            'title': solution_data.get('title', 'Untitled'),
            'files': [],
            'thumbnails': []
        }
        
        for file in files:
            file_ext = file.get('name', '').split('.')[-1].lower()
            file_info = {
                'name': file.get('name'),
                'path': file.get('path'),
                'size': file.get('size', 0),
                'type': self._detect_file_type(file_ext)
            }
            
            # Genera thumbnail per file visualizzabili
            if file_info['type'] in ['image', '3d_model', 'schematic']:
                file_info['thumbnail'] = self._generate_thumbnail(file)
            
            preview['files'].append(file_info)
        
        return preview
    
    def _detect_file_type(self, extension: str) -> str:
        """Rileva tipo di file dall'estensione"""
        type_mapping = {
            'png': 'image', 'jpg': 'image', 'jpeg': 'image', 'svg': 'image',
            'stl': '3d_model', 'step': '3d_model', 'stp': '3d_model',
            'kicad_pcb': 'schematic', 'kicad_sch': 'schematic',
            'brd': 'schematic', 'sch': 'schematic',
            'py': 'code', 'js': 'code', 'java': 'code', 'cpp': 'code',
            'md': 'document', 'txt': 'document', 'pdf': 'document'
        }
        return type_mapping.get(extension, 'unknown')
    
    # ⭐ NUOVO: Metodi per gestire tutti i tipi di contenuto
    
    def organize_files_by_content_type(self, files: List[Dict], content_type: str) -> Dict[str, List[Dict]]:
        """
        Organizza file per tipo di contenuto nelle directory appropriate
        Returns: Dict con struttura {directory: [files]}
        """
        organized = {}
        structure = PROJECT_STRUCTURE.get(content_type, PROJECT_STRUCTURE['mixed'])
        
        for file in files:
            extension = file.get('name', '').split('.')[-1].lower()
            target_dir = self._determine_target_directory(extension, content_type, structure)
            
            if target_dir not in organized:
                organized[target_dir] = []
            
            organized[target_dir].append(file)
        
        return organized
    
    def _determine_target_directory(self, extension: str, content_type: str, structure: Dict) -> str:
        """Determina directory appropriata per un file"""
        ext_with_dot = f'.{extension}'
        
        if content_type == 'design':
            # Loghi e vettoriali
            if ext_with_dot in ['.svg', '.ai', '.eps']:
                return 'logos' if 'logo' in extension else 'assets'
            # Mockup
            elif ext_with_dot in ['.fig', '.xd', '.sketch']:
                return 'mockups'
            # Illustrazioni
            elif ext_with_dot in ['.png', '.jpg', '.jpeg']:
                return 'illustrations'
            # Source files
            elif ext_with_dot in ['.psd', '.ai']:
                return 'assets'
            else:
                return 'exports'
        
        elif content_type == 'documentation':
            if ext_with_dot in ['.ppt', '.pptx', '.key']:
                return 'presentations'
            elif ext_with_dot in ['.pdf', '.docx']:
                return 'business' if any(k in ['business', 'plan'] for k in extension.lower()) else 'guides'
            elif ext_with_dot in ['.md', '.txt']:
                return 'technical'
            else:
                return 'guides'
        
        elif content_type == 'media':
            if ext_with_dot in SUPPORTED_FILE_FORMATS['media']['video']:
                return 'videos'
            elif ext_with_dot in SUPPORTED_FILE_FORMATS['media']['audio']:
                return 'audio'
            elif ext_with_dot in ['.gif', '.apng']:
                return 'animations'
            elif ext_with_dot in SUPPORTED_FILE_FORMATS['media']['images']:
                return 'images'
            else:
                return 'promotional'
        
        elif content_type == 'hardware':
            if ext_with_dot in SUPPORTED_FILE_FORMATS['hardware']['kicad'] or \
               ext_with_dot in SUPPORTED_FILE_FORMATS['hardware']['eagle']:
                return 'schematics'
            elif ext_with_dot in SUPPORTED_FILE_FORMATS['hardware']['cad_3d']:
                return '3d-models'
            elif ext_with_dot in SUPPORTED_FILE_FORMATS['hardware']['gerber']:
                return 'pcb'
            elif ext_with_dot in ['.csv', '.xlsx', '.txt']:
                return 'bom'
            else:
                return 'docs'
        
        # Default per software o mixed
        return list(structure.keys())[0] if structure else 'src'
    
    def validate_file_upload(self, file_data: Dict, content_type: str) -> Dict[str, Any]:
        """
        Valida un file prima dell'upload
        Returns: {'valid': bool, 'error': str, 'size_mb': float}
        """
        filename = file_data.get('name', '')
        file_size = file_data.get('size', 0)
        extension = filename.split('.')[-1].lower()
        ext_with_dot = f'.{extension}'
        
        # Check estensione supportata
        content_type_detected = get_content_type_from_extension(ext_with_dot)
        
        if content_type_detected == 'mixed' and content_type != 'mixed':
            return {
                'valid': False,
                'error': f'File type .{extension} not supported for {content_type} projects',
                'size_mb': file_size / (1024 * 1024)
            }
        
        # Check dimensione
        size_limit_mb = FILE_SIZE_LIMITS.get(content_type, FILE_SIZE_LIMITS['default'])
        size_mb = file_size / (1024 * 1024)
        
        if size_mb > size_limit_mb:
            return {
                'valid': False,
                'error': f'File size {size_mb:.1f}MB exceeds limit of {size_limit_mb}MB',
                'size_mb': size_mb
            }
        
        return {
            'valid': True,
            'error': None,
            'size_mb': size_mb,
            'content_type': content_type_detected
        }
    
    def get_file_preview_info(self, file_data: Dict) -> Dict[str, Any]:
        """
        Ottiene informazioni per preview del file
        Returns: Dict con tipo, icona, se è previewable, etc.
        """
        filename = file_data.get('name', '')
        extension = filename.split('.')[-1].lower()
        ext_with_dot = f'.{extension}'
        content_type = get_content_type_from_extension(ext_with_dot)
        
        preview_info = {
            'filename': filename,
            'extension': extension,
            'content_type': content_type,
            'icon': self._get_file_icon(content_type, extension),
            'previewable': self._is_previewable(extension),
            'preview_type': self._get_preview_type(extension)
        }
        
        return preview_info
    
    def _get_file_icon(self, content_type: str, extension: str) -> str:
        """Ritorna emoji/icona appropriata per il tipo di file"""
        icons = {
            'software': '💻',
            'hardware': '🔧',
            'design': '🎨',
            'documentation': '📄',
            'media': '🎬'
        }
        
        # Icone specifiche per estensione
        specific_icons = {
            'py': '🐍', 'js': '📜', 'html': '🌐', 'css': '🎨',
            'mp4': '🎥', 'mp3': '🎵', 'pdf': '📕',
            'psd': '🖼️', 'ai': '✨', 'fig': '🎯',
            'stl': '📐', 'pcb': '⚡'
        }
        
        return specific_icons.get(extension, icons.get(content_type, '📎'))
    
    def _is_previewable(self, extension: str) -> bool:
        """Controlla se il file è visualizzabile in browser"""
        previewable = [
            'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp',  # Immagini
            'mp4', 'webm',  # Video
            'mp3', 'wav', 'ogg',  # Audio
            'pdf',  # Documenti
            'md', 'txt',  # Testo
            'json', 'xml', 'yaml'  # Dati
        ]
        return extension in previewable
    
    def _get_preview_type(self, extension: str) -> str:
        """Determina il tipo di preview da usare"""
        if extension in ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp']:
            return 'image'
        elif extension in ['mp4', 'webm']:
            return 'video'
        elif extension in ['mp3', 'wav', 'ogg']:
            return 'audio'
        elif extension == 'pdf':
            return 'pdf'
        elif extension in ['md', 'txt', 'json', 'xml', 'yaml']:
            return 'text'
        elif extension in ['stl', 'obj']:
            return '3d_model'
        else:
            return 'download'
    
    def _generate_thumbnail(self, file: Dict) -> Optional[str]:
        """Genera thumbnail per file (placeholder per ora)"""
        # TODO: Implementare generazione thumbnail reale
        return None
    
    def verify_repo_access(self, repo_full_name: str) -> bool:
        """
        Verifica se il repository esiste e se abbiamo accesso
        
        Args:
            repo_full_name: Nome completo del repo (owner/name)
        
        Returns:
            True se il repo esiste ed è accessibile, False altrimenti
        """
        try:
            url = f"{self.api_base}/repos/{repo_full_name}"
            response = self._make_request('GET', url)
            
            if response and response.status_code == 200:
                logger.info(f"Repository {repo_full_name} verificato con successo")
                return True
            else:
                logger.warning(f"Repository {repo_full_name} non accessibile")
                return False
        except Exception as e:
            logger.error(f"Errore verifica repository {repo_full_name}: {e}")
            return False
    


# Singleton instance
_github_service = None

def get_github_service() -> GitHubService:
    """Factory per ottenere istanza singleton del servizio"""
    global _github_service
    if _github_service is None:
        _github_service = GitHubService()
    return _github_service

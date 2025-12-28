"""
GitHub Auto-Publisher Service
=============================

Permette a CHIUNQUE di pubblicare soluzioni su GitHub senza conoscere Git/PR.

Flow:
1. Utente incolla codice in textarea
2. Sistema crea automaticamente:
   - Fork del repository (se non esiste)
   - Branch con nome univoco
   - Commit con il codice
   - Pull Request verso repo originale
3. Soluzione pubblicata su KickThisUSS con link alla PR

Modalità Operative:
- BOT MODE: Un bot GitHub fa fork/PR per conto utente
- USER MODE: Usa token GitHub personale dell'utente
"""

import os
import base64
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import requests
from flask import current_app

from utils.github_config_loader import get_content_type_from_extension


class GitHubAutoPublisher:
    """
    Servizio per creare automaticamente PR su GitHub da contenuto testuale
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Args:
            github_token: Token GitHub personale o bot token
        """
        self.token = github_token or os.getenv('GITHUB_BOT_TOKEN')
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
    def publish_solution_auto(
        self,
        repo_url: str,
        content_data: Dict[str, any],
        task_info: Dict[str, str],
        user_info: Dict[str, str]
    ) -> Dict[str, any]:
        """
        Pubblica una soluzione creando automaticamente PR su GitHub.
        
        Args:
            repo_url: URL repository GitHub (es: https://github.com/owner/repo)
            content_data: {
                'type': 'code' | 'files',
                'code': 'codice sorgente',  # se type=code
                'files': [{...}],  # se type=files
                'file_path': 'path/to/file.py',  # dove salvare il codice
                'content_type': 'software' | 'design' | ...
            }
            task_info: {
                'task_id': 123,
                'title': 'Implementa login',
                'description': '...'
            }
            user_info: {
                'username': 'mario_rossi',
                'email': 'mario@example.com',
                'github_username': 'mariorossi' (opzionale)
            }
            
        Returns:
            {
                'success': True,
                'pr_url': 'https://github.com/owner/repo/pull/456',
                'pr_number': 456,
                'branch_name': 'kickstorm/task-123-mario-rossi',
                'fork_url': 'https://github.com/bot/repo' (se bot mode)
            }
        """
        try:
            # 1. Parse repository info
            owner, repo = self._parse_repo_url(repo_url)
            
            # 2. Check se repo esiste ed è accessibile
            repo_info = self._get_repo_info(owner, repo)
            if not repo_info:
                return {
                    'success': False,
                    'error': 'Repository non trovato o non accessibile'
                }
            
            # 3. Determina chi fa il fork (bot o utente)
            fork_owner = self._get_fork_owner(user_info)
            
            # 4. Crea/ottieni fork
            fork_result = self._ensure_fork(owner, repo, fork_owner)
            if not fork_result['success']:
                return fork_result
            
            fork_full_name = fork_result['fork_full_name']
            
            # 5. Genera branch name univoco
            branch_name = self._generate_branch_name(task_info, user_info)
            
            # 6. Ottieni default branch e ultimo commit
            default_branch = repo_info.get('default_branch', 'main')
            base_sha = self._get_branch_sha(owner, repo, default_branch)
            
            # 7. Crea branch nel fork
            branch_created = self._create_branch(
                fork_full_name, 
                branch_name, 
                base_sha
            )
            if not branch_created:
                return {
                    'success': False,
                    'error': 'Impossibile creare branch'
                }
            
            # 8. Prepara file da committare
            files_to_commit = self._prepare_files(content_data, task_info)
            
            # 9. Commit file nel branch
            commit_result = self._commit_files(
                fork_full_name,
                branch_name,
                files_to_commit,
                task_info,
                user_info
            )
            
            if not commit_result['success']:
                return commit_result
            
            # 10. Crea Pull Request
            pr_result = self._create_pull_request(
                owner,
                repo,
                fork_owner,
                branch_name,
                default_branch,
                task_info,
                user_info,
                content_data
            )
            
            if pr_result['success']:
                # 11. Aggiungi labels e commenti
                self._enhance_pull_request(
                    owner,
                    repo,
                    pr_result['pr_number'],
                    task_info,
                    content_data
                )
            
            return pr_result
            
        except Exception as e:
            current_app.logger.error(f"Error in publish_solution_auto: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Errore durante la pubblicazione: {str(e)}'
            }
    
    def _parse_repo_url(self, repo_url: str) -> Tuple[str, str]:
        """
        Estrae owner e repo da URL GitHub
        
        Examples:
            https://github.com/owner/repo -> ('owner', 'repo')
            https://github.com/owner/repo.git -> ('owner', 'repo')
            git@github.com:owner/repo.git -> ('owner', 'repo')
        """
        # Clean URL
        repo_url = repo_url.strip().rstrip('/')
        
        # Pattern matching
        patterns = [
            r'github\.com[:/]([^/]+)/([^/.]+)',  # HTTPS or SSH
            r'^([^/]+)/([^/]+)$'  # owner/repo format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, repo_url)
            if match:
                owner, repo = match.groups()
                # Remove .git suffix if present
                repo = repo.replace('.git', '')
                return owner, repo
        
        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
    
    def _get_repo_info(self, owner: str, repo: str) -> Optional[Dict]:
        """Ottiene informazioni repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        return None
    
    def _get_fork_owner(self, user_info: Dict) -> str:
        """
        Determina chi deve fare il fork:
        - Se utente ha github_username configurato -> usa quello
        - Altrimenti usa bot account
        """
        if user_info.get('github_username'):
            return user_info['github_username']
        
        # Usa bot account (configurato in .env)
        bot_username = os.getenv('GITHUB_BOT_USERNAME', 'kickstorm-bot')
        return bot_username
    
    def _ensure_fork(self, owner: str, repo: str, fork_owner: str) -> Dict:
        """
        Assicura che esista un fork del repository.
        Se non esiste, lo crea.
        """
        # 1. Check se fork già esiste
        fork_url = f"{self.base_url}/repos/{fork_owner}/{repo}"
        response = requests.get(fork_url, headers=self.headers)
        
        if response.status_code == 200:
            fork_data = response.json()
            # Verifica che sia effettivamente un fork del repo originale
            parent = fork_data.get('parent', {})
            if parent.get('full_name') == f"{owner}/{repo}":
                return {
                    'success': True,
                    'fork_full_name': fork_data['full_name'],
                    'fork_url': fork_data['html_url']
                }
        
        # 2. Fork non esiste, crealo
        create_fork_url = f"{self.base_url}/repos/{owner}/{repo}/forks"
        response = requests.post(create_fork_url, headers=self.headers)
        
        if response.status_code == 202:  # Fork creation accepted
            fork_data = response.json()
            return {
                'success': True,
                'fork_full_name': fork_data['full_name'],
                'fork_url': fork_data['html_url']
            }
        
        return {
            'success': False,
            'error': f"Impossibile creare fork: {response.json().get('message', 'Unknown error')}"
        }
    
    def _generate_branch_name(self, task_info: Dict, user_info: Dict) -> str:
        """
        Genera nome branch univoco
        
        Format: kickstorm/task-{task_id}-{username}-{timestamp}
        """
        task_id = task_info['task_id']
        username = user_info['username'].lower().replace(' ', '-')[:20]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        return f"kickstorm/task-{task_id}-{username}-{timestamp}"
    
    def _get_branch_sha(self, owner: str, repo: str, branch: str) -> str:
        """Ottiene SHA dell'ultimo commit di un branch"""
        url = f"{self.base_url}/repos/{owner}/{repo}/git/ref/heads/{branch}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()['object']['sha']
        
        raise ValueError(f"Branch {branch} not found")
    
    def _create_branch(self, fork_full_name: str, branch_name: str, base_sha: str) -> bool:
        """Crea nuovo branch nel fork"""
        url = f"{self.base_url}/repos/{fork_full_name}/git/refs"
        
        data = {
            'ref': f'refs/heads/{branch_name}',
            'sha': base_sha
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        return response.status_code == 201
    
    def _prepare_files(self, content_data: Dict, task_info: Dict) -> List[Dict]:
        """
        Prepara lista file da committare
        
        Returns:
            [
                {
                    'path': 'src/auth.py',
                    'content': 'def login(): ...',
                    'encoding': 'utf-8'
                },
                ...
            ]
        """
        files = []
        
        if content_data['type'] == 'code':
            # Codice singolo incollato
            file_path = content_data.get('file_path', self._guess_file_path(content_data))
            files.append({
                'path': file_path,
                'content': content_data['code'],
                'encoding': 'utf-8'
            })
            
        elif content_data['type'] == 'files':
            # File multipli caricati
            for file_data in content_data['files']:
                files.append({
                    'path': file_data['path'],
                    'content': file_data['content'],
                    'encoding': file_data.get('encoding', 'utf-8')
                })
        
        # Aggiungi README se non presente
        if not any(f['path'].lower() == 'readme.md' for f in files):
            readme_content = self._generate_solution_readme(task_info, content_data)
            files.append({
                'path': 'SOLUTION_README.md',
                'content': readme_content,
                'encoding': 'utf-8'
            })
        
        return files
    
    def _guess_file_path(self, content_data: Dict) -> str:
        """
        Indovina il path del file basandosi sul contenuto
        """
        code = content_data.get('code', '')
        content_type = content_data.get('content_type', 'software')
        
        # Detect linguaggio dal codice
        if 'def ' in code and 'import ' in code:
            return 'solution.py'
        elif 'function' in code or 'const ' in code or 'let ' in code:
            return 'solution.js'
        elif 'public class' in code or 'public static void' in code:
            return 'Solution.java'
        elif '#include' in code:
            return 'solution.cpp'
        elif '<?php' in code:
            return 'solution.php'
        
        # Fallback per content type
        extensions = {
            'software': 'solution.txt',
            'design': 'design_notes.md',
            'documentation': 'documentation.md',
            'hardware': 'hardware_spec.md',
            'media': 'media_description.md'
        }
        
        return extensions.get(content_type, 'solution.txt')
    
    def _commit_files(
        self,
        fork_full_name: str,
        branch_name: str,
        files: List[Dict],
        task_info: Dict,
        user_info: Dict
    ) -> Dict:
        """
        Crea commit con file nel branch
        """
        try:
            for file_data in files:
                # Crea o aggiorna file
                success = self._create_or_update_file(
                    fork_full_name,
                    branch_name,
                    file_data['path'],
                    file_data['content'],
                    f"Add {file_data['path']} for task #{task_info['task_id']}",
                    user_info
                )
                
                if not success:
                    return {
                        'success': False,
                        'error': f"Failed to commit {file_data['path']}"
                    }
            
            return {'success': True}
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Commit error: {str(e)}"
            }
    
    def _create_or_update_file(
        self,
        repo_full_name: str,
        branch: str,
        file_path: str,
        content: str,
        commit_message: str,
        user_info: Dict
    ) -> bool:
        """Crea o aggiorna un singolo file"""
        url = f"{self.base_url}/repos/{repo_full_name}/contents/{file_path}"
        
        # Encode content to base64
        content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        # Check se file esiste già
        response = requests.get(url, headers=self.headers, params={'ref': branch})
        
        data = {
            'message': commit_message,
            'content': content_encoded,
            'branch': branch,
            'committer': {
                'name': user_info.get('username', 'KickStorm User'),
                'email': user_info.get('email', 'noreply@kickstorm.com')
            }
        }
        
        if response.status_code == 200:
            # File esiste, aggiornalo
            data['sha'] = response.json()['sha']
        
        # Create or update
        response = requests.put(url, headers=self.headers, json=data)
        return response.status_code in [200, 201]
    
    def _create_pull_request(
        self,
        base_owner: str,
        base_repo: str,
        head_owner: str,
        head_branch: str,
        base_branch: str,
        task_info: Dict,
        user_info: Dict,
        content_data: Dict
    ) -> Dict:
        """Crea Pull Request"""
        url = f"{self.base_url}/repos/{base_owner}/{base_repo}/pulls"
        
        title = f"[KickStorm] Solution for Task #{task_info['task_id']}: {task_info['title']}"
        body = self._generate_pr_body(task_info, user_info, content_data)
        
        data = {
            'title': title,
            'head': f"{head_owner}:{head_branch}",
            'base': base_branch,
            'body': body,
            'maintainer_can_modify': True
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        
        if response.status_code == 201:
            pr_data = response.json()
            return {
                'success': True,
                'pr_url': pr_data['html_url'],
                'pr_number': pr_data['number'],
                'branch_name': head_branch
            }
        
        return {
            'success': False,
            'error': f"PR creation failed: {response.json().get('message', 'Unknown error')}"
        }
    
    def _generate_pr_body(self, task_info: Dict, user_info: Dict, content_data: Dict) -> str:
        """Genera descrizione Pull Request"""
        return f"""## 🎯 KickStorm Solution

**Task ID**: #{task_info['task_id']}  
**Task Title**: {task_info['title']}  
**Submitted by**: {user_info['username']}  
**Content Type**: {content_data.get('content_type', 'software').title()}

### 📝 Task Description
{task_info.get('description', 'N/A')[:300]}...

### ✨ Solution Overview
This Pull Request was automatically created via KickStorm platform.

---

### 🔍 How to Review
1. Check the code/files in the "Files changed" tab
2. Test locally if needed
3. Leave feedback in comments
4. Approve or request changes

### 🚀 Next Steps
- [ ] Code review by maintainer
- [ ] Tests pass (if CI/CD enabled)
- [ ] Merge when approved

---

**Generated by** [KickStorm](https://kickstorm.com) - Collaborative Innovation Platform  
**🤖 Auto-PR**: This PR was created automatically to simplify contribution for non-Git experts.
"""
    
    def _generate_solution_readme(self, task_info: Dict, content_data: Dict) -> str:
        """Genera README per la soluzione"""
        return f"""# Solution for Task #{task_info['task_id']}

## Task: {task_info['title']}

**Content Type**: {content_data.get('content_type', 'software').title()}  
**Created**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Description
{task_info.get('description', 'No description provided')}

## Solution Files
Check the files in this branch for the complete solution.

---

*This solution was submitted via KickStorm platform.*
"""
    
    def _enhance_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        task_info: Dict,
        content_data: Dict
    ):
        """Aggiungi labels e commenti alla PR"""
        # Add labels
        labels_url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/labels"
        labels = [
            'kickstorm',
            f"task-{task_info['task_id']}",
            content_data.get('content_type', 'software')
        ]
        
        requests.post(labels_url, headers=self.headers, json={'labels': labels})
        
        # Add comment with instructions
        comment_url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        comment_body = """👋 **Welcome KickStorm Contributor!**

This PR was automatically generated. Here's what happens next:

1. ⏳ **Automated checks** will run (if configured)
2. 👀 **Maintainer review** - project owner will review your solution
3. 💬 **Feedback** - you may receive comments/requests for changes
4. ✅ **Approval** - once approved, PR will be merged
5. 🎉 **Points awarded** - you'll receive reputation points on KickStorm!

Need help? Check the [contribution guide](https://docs.kickstorm.com/contributing).
"""
        
        requests.post(comment_url, headers=self.headers, json={'body': comment_body})


# ============================================
# Helper Functions
# ============================================

def extract_code_from_textarea(textarea_content: str, content_type: str) -> Dict:
    """
    Estrae codice/contenuto da textarea e prepara per auto-PR
    
    Args:
        textarea_content: Contenuto incollato dall'utente
        content_type: Tipo (software, design, documentation, etc.)
    
    Returns:
        Dict pronto per GitHubAutoPublisher.publish_solution_auto()
    """
    return {
        'type': 'code',
        'code': textarea_content,
        'content_type': content_type,
        'file_path': None  # Will be auto-detected
    }


def extract_uploaded_files(file_list: List, content_type: str) -> Dict:
    """
    Prepara file caricati per auto-PR
    
    Args:
        file_list: Lista di werkzeug.FileStorage objects
        content_type: Tipo contenuto
    
    Returns:
        Dict pronto per GitHubAutoPublisher.publish_solution_auto()
    """
    files = []
    
    for file_storage in file_list:
        if file_storage and file_storage.filename:
            content = file_storage.read()
            
            # Decode se è testo
            try:
                content_str = content.decode('utf-8')
                encoding = 'utf-8'
            except UnicodeDecodeError:
                # File binario, usa base64
                content_str = base64.b64encode(content).decode('utf-8')
                encoding = 'base64'
            
            files.append({
                'path': file_storage.filename,
                'content': content_str,
                'encoding': encoding
            })
            
            # Reset file pointer
            file_storage.seek(0)
    
    return {
        'type': 'files',
        'files': files,
        'content_type': content_type
    }

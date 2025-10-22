import logging
from typing import Dict, List
from tasks import celery
from services.github_service import get_github_service
from utils.hardware_parser import HardwareFileHandler

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3)
def sync_project_to_github(self, project_id: int, project_data: Dict):
    """
    Task asincrono per creare repository GitHub per un progetto
    Non blocca la creazione del progetto se fallisce
    """
    try:
        from models import Project
        from app import db
        
        github_service = get_github_service()
        
        # Crea repository
        repo_url = github_service.create_project_repo(project_id, project_data)
        
        if repo_url:
            # Aggiorna progetto con URL repo
            project = Project.query.get(project_id)
            if project:
                project.github_repo_url = repo_url
                project.github_sync_enabled = True
                db.session.commit()
                logger.info(f"Project {project_id} synced to GitHub: {repo_url}")
        else:
            logger.warning(f"Failed to create GitHub repo for project {project_id}")
            
    except Exception as exc:
        logger.error(f"Error syncing project {project_id} to GitHub: {exc}")
        raise self.retry(exc=exc, countdown=60)  # Retry dopo 1 minuto


@celery.task(bind=True, max_retries=3)
def sync_solution_to_github(self, solution_id: int):
    """
    Task asincrono per sincronizzare soluzione su GitHub
    Crea branch, carica file, crea PR
    """
    try:
        from models import Solution, Project
        from app import db
        
        solution = Solution.query.get(solution_id)
        if not solution:
            logger.error(f"Solution {solution_id} not found")
            return
        
        project = solution.project
        if not project.github_repo_url:
            logger.warning(f"Project {project.id} has no GitHub repo")
            return
        
        github_service = get_github_service()
        repo_name = project.github_repo_url.split('/')[-1]
        
        # Prepara dati soluzione
        solution_data = {
            'title': solution.title,
            'description': solution.description,
            'category': solution.category,
            'author': solution.user.username if solution.user else 'Anonymous',
            'type': project.project_type
        }
        
        # Crea branch per soluzione
        branch_name = github_service.create_solution_branch(
            project.id,
            solution.id,
            solution_data
        )
        
        if not branch_name:
            logger.error(f"Failed to create branch for solution {solution_id}")
            return
        
        # Prepara file da caricare
        files_to_upload = []
        
        # Se è una soluzione software
        if solution.code_content:
            files_to_upload.append({
                'name': f"solution.{solution.language or 'txt'}",
                'content': solution.code_content,
                'path': f"src/solution.{solution.language or 'txt'}"
            })
        
        # Se ci sono file hardware
        if hasattr(solution, 'files') and solution.files:
            handler = HardwareFileHandler()
            organized_files = handler.organize_files(solution.files, project.project_type)
            
            for category, files in organized_files.items():
                for file in files:
                    files_to_upload.append(file)
        
        # README con descrizione
        readme_content = f"""# {solution.title}

## Description
{solution.description}

## Author
{solution_data['author']}

## Category
{solution.category}

---
*Submitted via KickThisUSS*
"""
        files_to_upload.append({
            'name': 'README.md',
            'content': readme_content,
            'path': 'README.md'
        })
        
        # Carica file
        github_service.upload_solution_files(repo_name, branch_name, files_to_upload)
        
        # Crea Pull Request
        pr_url = github_service.create_pull_request(repo_name, branch_name, solution_data)
        
        if pr_url:
            # Aggiorna soluzione con info GitHub
            solution.github_branch_name = branch_name
            solution.github_pr_url = pr_url
            db.session.commit()
            logger.info(f"Solution {solution_id} synced to GitHub: {pr_url}")
        
    except Exception as exc:
        logger.error(f"Error syncing solution {solution_id} to GitHub: {exc}")
        raise self.retry(exc=exc, countdown=120)  # Retry dopo 2 minuti


@celery.task
def sync_comments_from_github(project_id: int, solution_id: int):
    """
    Sincronizza commenti da GitHub PR verso database locale
    Permette discussioni bidirezionali
    """
    try:
        from models import Solution, Comment, User
        from app import db
        
        solution = Solution.query.get(solution_id)
        if not solution or not solution.github_pr_url:
            return
        
        github_service = get_github_service()
        project = solution.project
        repo_name = project.github_repo_url.split('/')[-1]
        pr_number = int(solution.github_pr_url.split('/')[-1])
        
        # Ottieni commenti da GitHub
        github_comments = github_service.sync_comments(repo_name, pr_number)
        
        # Importa commenti non ancora presenti
        for gh_comment in github_comments:
            # Check se commento già esiste
            existing = Comment.query.filter_by(
                github_comment_id=gh_comment['id']
            ).first()
            
            if not existing:
                # Trova o crea utente
                user = User.query.filter_by(
                    github_username=gh_comment['user']['login']
                ).first()
                
                if not user:
                    # Crea placeholder user per utente GitHub
                    user = User(
                        username=gh_comment['user']['login'],
                        email=f"{gh_comment['user']['login']}@github.placeholder",
                        github_username=gh_comment['user']['login']
                    )
                    db.session.add(user)
                
                # Crea commento
                comment = Comment(
                    content=gh_comment['body'],
                    user_id=user.id,
                    solution_id=solution_id,
                    github_comment_id=gh_comment['id'],
                    created_at=gh_comment['created_at']
                )
                db.session.add(comment)
        
        db.session.commit()
        logger.info(f"Comments synced for solution {solution_id}")
        
    except Exception as e:
        logger.error(f"Error syncing comments: {e}")


@celery.task
def cleanup_old_branches(project_id: int):
    """
    Task di pulizia: elimina branch vecchi di soluzioni rifiutate/archiviate
    """
    try:
        from models import Solution, Project
        from datetime import datetime, timedelta
        
        project = Project.query.get(project_id)
        if not project or not project.github_repo_url:
            return
        
        # Trova soluzioni vecchie (>90 giorni) e non approvate
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        old_solutions = Solution.query.filter(
            Solution.project_id == project_id,
            Solution.status != 'approved',
            Solution.created_at < cutoff_date,
            Solution.github_branch_name.isnot(None)
        ).all()
        
        github_service = get_github_service()
        repo_name = project.github_repo_url.split('/')[-1]
        
        for solution in old_solutions:
            # Elimina branch (chiude automaticamente PR)
            try:
                url = f"{github_service.api_base}/repos/{github_service.org}/{repo_name}/git/refs/heads/{solution.github_branch_name}"
                github_service._make_request('DELETE', url)
                logger.info(f"Deleted old branch: {solution.github_branch_name}")
            except Exception as e:
                logger.warning(f"Failed to delete branch: {e}")
        
    except Exception as e:
        logger.error(f"Error cleaning up branches: {e}")

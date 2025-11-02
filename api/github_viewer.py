from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from models import Project, Solution
from services.github_service import get_github_service
from config.github_config import GITHUB_ENABLED

api_github_bp = Blueprint('api_github', __name__, url_prefix='/api/github')


@api_github_bp.route('/project/<int:project_id>/files')
def get_project_files(project_id):
    """API per recuperare lista file da GitHub senza mostrare GitHub"""
    if not GITHUB_ENABLED:
        return jsonify({'files': [], 'enabled': False})
    
    project = Project.query.get_or_404(project_id)
    
    if not project.github_repo_url:
        return jsonify({'files': [], 'message': 'No repository linked'})
    
    try:
        github_service = get_github_service()
        repo_name = project.github_repo_url.split('/')[-1]
        
        path = request.args.get('path', '')
        branch = request.args.get('branch', 'main')
        
        files = github_service.list_repo_files(repo_name, path, branch)
        
        return jsonify({
            'files': files,
            'project_id': project_id,
            'path': path
        })
    
    except Exception as e:
        current_app.logger.error(f"Error fetching files: {e}")
        return jsonify({'error': 'Failed to fetch files'}), 500


@api_github_bp.route('/project/<int:project_id>/file/content')
def get_file_content(project_id):
    """Ottiene contenuto di un file specifico"""
    if not GITHUB_ENABLED:
        return jsonify({'content': None, 'enabled': False})
    
    project = Project.query.get_or_404(project_id)
    
    if not project.github_repo_url:
        return jsonify({'error': 'No repository linked'}), 404
    
    file_path = request.args.get('path')
    branch = request.args.get('branch', 'main')
    
    if not file_path:
        return jsonify({'error': 'File path required'}), 400
    
    try:
        github_service = get_github_service()
        repo_name = project.github_repo_url.split('/')[-1]
        
        content = github_service.get_file_content(repo_name, file_path, branch)
        
        if content is None:
            return jsonify({'error': 'File not found'}), 404
        
        return jsonify({
            'content': content,
            'path': file_path,
            'branch': branch
        })
    
    except Exception as e:
        current_app.logger.error(f"Error fetching file content: {e}")
        return jsonify({'error': 'Failed to fetch file'}), 500


@api_github_bp.route('/solution/<int:solution_id>/preview')
def preview_solution(solution_id):
    """Genera preview di soluzione hardware/software"""
    if not GITHUB_ENABLED:
        return jsonify({'preview': None, 'enabled': False})
    
    solution = Solution.query.get_or_404(solution_id)
    
    try:
        github_service = get_github_service()
        
        # Prepara dati soluzione
        solution_data = {
            'type': solution.project.project_type,
            'title': solution.title,
            'description': solution.description
        }
        
        # Recupera file se branch GitHub esiste
        files = []
        if solution.github_branch_name:
            project = solution.project
            repo_name = project.github_repo_url.split('/')[-1]
            files = github_service.list_repo_files(
                repo_name, 
                '', 
                solution.github_branch_name
            )
        
        preview = github_service.generate_preview(solution_data, files)
        
        return jsonify({
            'preview': preview,
            'solution_id': solution_id,
            'github_url': solution.github_pr_url
        })
    
    except Exception as e:
        current_app.logger.error(f"Error generating preview: {e}")
        return jsonify({'error': 'Failed to generate preview'}), 500


@api_github_bp.route('/solution/<int:solution_id>/status')
def solution_github_status(solution_id):
    """Verifica stato sincronizzazione GitHub di una soluzione"""
    solution = Solution.query.get_or_404(solution_id)
    
    status = {
        'synced': solution.github_pr_url is not None,
        'branch': solution.github_branch_name,
        'pr_url': solution.github_pr_url,
        'commit_sha': solution.github_commit_sha,
        'synced_at': solution.github_synced_at.isoformat() if solution.github_synced_at else None
    }
    
    return jsonify(status)


@api_github_bp.route('/project/<int:project_id>/toggle-sync', methods=['POST'])
@login_required
def toggle_github_sync(project_id):
    """Permette all'utente di abilitare/disabilitare sync GitHub per un progetto"""
    from app import db
    
    project = Project.query.get_or_404(project_id)
    
    # Verifica che l'utente sia il proprietario
    if project.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    enabled = request.json.get('enabled', True)
    project.github_sync_enabled = enabled
    db.session.commit()
    
    return jsonify({
        'project_id': project_id,
        'github_sync_enabled': project.github_sync_enabled,
        'message': 'GitHub sync ' + ('enabled' if enabled else 'disabled')
    })


@api_github_bp.route('/project/<int:project_id>/connect-repo', methods=['POST'])
@login_required
def connect_repo(project_id):
    """Collega un repository GitHub esistente al progetto, o lo crea se non esiste"""
    from app import db
    from flask_login import current_user
    
    project = Project.query.get_or_404(project_id)
    
    # Verifica che l'utente sia il creatore del progetto
    if project.creator_id != current_user.id:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    data = request.json
    repo_full_name = data.get('repo_full_name')
    auto_create = data.get('auto_create', False)  # Flag per creare automaticamente
    
    if not repo_full_name or '/' not in repo_full_name:
        return jsonify({'success': False, 'message': 'Nome repository non valido'}), 400
    
    # Verifica che il repository esista su GitHub
    if GITHUB_ENABLED:
        try:
            github_service = get_github_service()
            # Test connessione al repo
            repo_exists = github_service.verify_repo_access(repo_full_name)
            
            if not repo_exists:
                if auto_create:
                    # Crea automaticamente il repository
                    repo_name = repo_full_name.split('/')[-1]
                    
                    result = github_service.create_repository(
                        repo_name=repo_name,
                        description=project.pitch or f"Repository per il progetto {project.name}",
                        private=project.private if hasattr(project, 'private') else False
                    )
                    
                    if not result:
                        return jsonify({
                            'success': False,
                            'message': 'Impossibile creare il repository automaticamente.'
                        }), 500
                    
                    # Repository creato con successo
                    current_app.logger.info(f"Repository {repo_full_name} creato automaticamente")
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Repository non trovato. Vuoi crearlo automaticamente?',
                        'can_create': True
                    }), 404
        except Exception as e:
            current_app.logger.error(f"Errore verifica repository: {e}")
            return jsonify({
                'success': False,
                'message': f'Errore durante la verifica: {str(e)}'
            }), 500
    
    # Salva il nome del repository
    project.github_repo_name = repo_full_name
    project.github_repo_url = f'https://github.com/{repo_full_name}'
    
    try:
        db.session.commit()
        message = 'Repository collegato con successo!'
        if not repo_exists and auto_create:
            message = 'Repository creato e collegato con successo!'
        
        return jsonify({
            'success': True,
            'message': message,
            'repo_name': repo_full_name,
            'created': auto_create and not repo_exists
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore salvataggio repository: {e}")
        return jsonify({
            'success': False,
            'message': 'Errore durante il salvataggio'
        }), 500


@api_github_bp.route('/project/<int:project_id>/sync-all-tasks', methods=['POST'])
@login_required
def sync_all_tasks(project_id):
    """Sincronizza tutti i task del progetto con GitHub Issues"""
    from app import db
    from models import Task
    from app.services.github_service import GitHubService
    
    project = Project.query.get_or_404(project_id)
    
    # Verifica che l'utente sia il creatore del progetto
    if project.creator_id != current_user.id:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    # Verifica che ci sia un repository collegato
    if not project.github_repo_name:
        return jsonify({
            'success': False,
            'message': 'Nessun repository collegato. Collega prima un repository.'
        }), 400
    
    if not GITHUB_ENABLED:
        return jsonify({
            'success': False,
            'message': 'Integrazione GitHub non abilitata'
        }), 400
    
    try:
        github_service = GitHubService()
        
        # Ottieni tutti i task del progetto
        tasks = Task.query.filter_by(project_id=project_id).all()
        
        synced_count = 0
        failed_count = 0
        skipped_count = 0
        
        for task in tasks:
            # Salta i task già sincronizzati di recente (nelle ultime 24 ore)
            from datetime import datetime, timedelta
            if task.github_synced_at and (datetime.utcnow() - task.github_synced_at) < timedelta(hours=24):
                skipped_count += 1
                continue
            
            # Sincronizza il task
            success = github_service.sync_task_to_github(task, project)
            if success:
                synced_count += 1
            else:
                failed_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Sincronizzazione completata!',
            'stats': {
                'synced': synced_count,
                'failed': failed_count,
                'skipped': skipped_count,
                'total': len(tasks)
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore sincronizzazione task: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante la sincronizzazione: {str(e)}'
        }), 500


@api_github_bp.route('/project/<int:project_id>/repo-stats', methods=['GET'])
@login_required
def get_repo_stats(project_id):
    """Ottieni statistiche del repository GitHub collegato"""
    from app.services.github_service import GitHubService
    
    project = Project.query.get_or_404(project_id)
    
    # Verifica che ci sia un repository collegato
    if not project.github_repo_name:
        return jsonify({
            'success': False,
            'message': 'Nessun repository collegato'
        }), 400
    
    if not GITHUB_ENABLED:
        return jsonify({
            'success': False,
            'message': 'Integrazione GitHub non abilitata'
        }), 400
    
    try:
        github_service = GitHubService()
        stats = github_service.get_repo_stats(project.github_repo_name)
        
        if not stats:
            return jsonify({
                'success': False,
                'message': 'Impossibile ottenere le statistiche'
            }), 500
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore ottenimento statistiche: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), 500

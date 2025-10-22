from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
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

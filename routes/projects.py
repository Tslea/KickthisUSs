from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from .. import db
from ..models import Project
from ..tasks.github_tasks import sync_project_to_github
from config.github_config import GITHUB_ENABLED

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        project_type = request.form.get('project_type')
        category = request.form.get('category')
        github_sync_enabled = request.form.get('github_sync_enabled') == 'on'
        
        # Validazione dei dati del progetto
        if not title or not description:
            return jsonify({'error': 'Title and description are required.'}), 400
        
        # Creazione del nuovo progetto
        new_project = Project(
            title=title,
            description=description,
            project_type=project_type,
            category=category,
            owner=current_user,
            github_sync_enabled=github_sync_enabled
        )
        
        # Salvataggio progetto
        db.session.add(new_project)
        db.session.commit()
        
        # GitHub sync (non blocca se fallisce)
        if GITHUB_ENABLED and new_project.github_sync_enabled:
            try:
                # Prepara dati per GitHub
                project_data = {
                    'title': new_project.title,
                    'description': new_project.description,
                    'project_type': new_project.project_type,
                    'category': new_project.category
                }
                
                # Task asincrono - non blocca risposta utente
                sync_project_to_github.delay(new_project.id, project_data)
                
                current_app.logger.info(f"GitHub sync queued for project {new_project.id}")
            except Exception as e:
                # Non blocca creazione progetto se GitHub fallisce
                current_app.logger.warning(f"GitHub sync failed for project {new_project.id}: {e}")
        
        return jsonify({'message': 'Project created successfully!', 'project_id': new_project.id}), 201
    
    return render_template('create_project.html')
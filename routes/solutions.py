from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from models import Solution, Project
from config.github_config import GITHUB_ENABLED
from tasks.github_tasks import sync_solution_to_github
from utils.hardware_parser import HardwareFileHandler

solutions_bp = Blueprint('solutions', __name__)

@solutions_bp.route('/project/<int:project_id>/solution/submit', methods=['GET', 'POST'])
@login_required
def submit_solution(project_id):
    # ...existing code per validazione e creazione soluzione...
    
    # CODICE ESISTENTE: Salvataggio soluzione
    db.session.add(solution)
    db.session.commit()
    
    # NUOVA SEZIONE: GitHub sync asincrono (non blocca)
    if GITHUB_ENABLED:
        project = Project.query.get(project_id)
        if project and project.github_sync_enabled:
            try:
                # Task asincrono per non bloccare risposta
                sync_solution_to_github.delay(solution.id)
                
                current_app.logger.info(f"GitHub sync queued for solution {solution.id}")
            except Exception as e:
                current_app.logger.warning(f"Failed to queue GitHub sync: {e}")
    
    # ...existing code per flash message e redirect...
    flash('Solution submitted successfully!', 'success')
    return redirect(url_for('solutions.view_solution', solution_id=solution.id))

@solutions_bp.route('/solution/<int:solution_id>')
def view_solution(solution_id):
    # ...existing code per recupero soluzione...
    
    solution = Solution.query.get_or_404(solution_id)
    
    # NUOVA SEZIONE: Sync commenti da GitHub se disponibile
    if GITHUB_ENABLED and solution.github_pr_url:
        try:
            from tasks.github_tasks import sync_comments_from_github
            sync_comments_from_github.delay(solution.project_id, solution.id)
        except Exception as e:
            current_app.logger.warning(f"Failed to sync comments: {e}")
    
    # ...existing code per rendering template...
    return render_template('solutions/view.html', solution=solution)
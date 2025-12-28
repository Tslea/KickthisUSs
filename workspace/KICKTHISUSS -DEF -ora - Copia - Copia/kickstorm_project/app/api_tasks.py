# app/api_tasks.py

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timezone

from . import db
from .models import Task, Solution, Activity, Comment # Aggiunto Comment
from .utils import clean_rich_text_field
from .ai_services import AI_SERVICE_AVAILABLE, analyze_solution_content
from .schemas import CommentCreateSchema, SolutionSubmitSchema, validate_request_data

api_tasks_bp = Blueprint('api_tasks', __name__)

# ... (add_solution_to_task rimane invariato) ...
@api_tasks_bp.route('/tasks/<int:task_id>/solutions', methods=['POST'])
@login_required
def add_solution_to_task(task_id):
    task = Task.query.get_or_404(task_id)
    if not request.is_json:
        return jsonify({"error": "La richiesta deve essere JSON."}), 415
    data = request.get_json()
    solution_content = data.get('solution_content')
    if not solution_content:
        return jsonify({"error": "Il contenuto della soluzione è obbligatorio."}), 400
    if task.status not in ['open', 'in_progress', 'submitted']:
        return jsonify({"error": f"Task non aperto a soluzioni (stato: {task.status})."}), 403
    try:
        new_solution = Solution(
            task_id=task.id,
            submitted_by_user_id=current_user.id, 
            solution_content=solution_content,
            status='submitted'
        )
        db.session.add(new_solution)
        db.session.flush()
        ai_analysis_error = None
        if AI_SERVICE_AVAILABLE and task.description:
            try:
                ai_results = analyze_solution_content(
                    task_title=task.title, task_description=task.description, solution_content=solution_content
                )
                if ai_results and ai_results.get("error") is None:
                    new_solution.ai_coherence_score = ai_results.get("coherence_score")
                    new_solution.ai_completeness_score = ai_results.get("completeness_score")
                    new_solution.ai_analysis_timestamp = datetime.now(timezone.utc)
                elif ai_results:
                    ai_analysis_error = ai_results.get("error")
            except Exception as e_ai:
                ai_analysis_error = str(e_ai)
        if task.status == 'open': task.status = 'submitted'
        activity = Activity(
            user_id=current_user.id, action='submit_solution',
            project_id=task.project_id, task_id=task.id, solution_id=new_solution.id
        )
        db.session.add(activity)

        # Notifica usando il servizio centralizzato
        from .models import Project
        from .services.notification_service import NotificationService
        project = db.session.get(Project, task.project_id)
        NotificationService.notify_solution_published(new_solution, task, project, current_user.id)

        db.session.commit()
        response_data = {"message": "Soluzione inviata con successo!", "solution_id": new_solution.id}
        if ai_analysis_error: response_data["ai_note"] = ai_analysis_error
        return jsonify(response_data), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"API Errore Aggiunta Soluzione: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server."}), 500

# --- NUOVA ROUTE PER I COMMENTI ---
@api_tasks_bp.route('/tasks/<int:task_id>/comments', methods=['POST'])
@login_required
def add_comment_to_task(task_id):
    """Aggiunge un commento a un task."""
    task = Task.query.get_or_404(task_id)
    if not request.is_json:
        return jsonify({"error": "La richiesta deve essere JSON."}), 415

    data = request.get_json()
    
    # Validazione con Pydantic
    is_valid, result = validate_request_data(CommentCreateSchema, data)
    if not is_valid:
        return jsonify(result), 400

    try:
        sanitized_content = clean_rich_text_field('comment', 'content', result.content)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        new_comment = Comment(
            content=sanitized_content,
            author_id=current_user.id,
            task_id=task.id
        )
        db.session.add(new_comment)

        # Registra anche l'attività (opzionale, ma coerente con il feed)
        activity = Activity(
            user_id=current_user.id,
            action='add_comment',
            project_id=task.project_id,
            task_id=task.id
        )
        db.session.add(activity)

        db.session.commit()

        # Ritorna il commento formattato per essere inserito dinamicamente nella pagina
        return jsonify({
            "message": "Commento aggiunto!",
            "comment": {
                "id": new_comment.id,
                "content": new_comment.content,
                "timestamp": new_comment.timestamp.isoformat(),
                "author": {
                    "id": current_user.id,
                    "username": current_user.username
                }
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"API Errore Aggiunta Commento: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server durante l'aggiunta del commento."}), 500


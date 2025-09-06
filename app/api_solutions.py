# app/api_solutions.py

from flask import Blueprint, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from . import db
from .models import Solution, Task, Project, Collaborator, Activity, TrainingData, Vote
from .decorators import role_required

api_solutions_bp = Blueprint('api_solutions', __name__)

@api_solutions_bp.route('/projects/<int:project_id>/solutions/<int:solution_id>/approve', methods=['POST'])
@login_required
@role_required('project_id', roles=['creator'])
def approve_solution_api(project_id, solution_id):
    solution = Solution.query.options(joinedload(Solution.submitter), joinedload(Solution.task).joinedload(Task.project)).get_or_404(solution_id)
    task = solution.task
    project = task.project
    
    if task.project_id != project_id:
        abort(404, description="La soluzione non appartiene a questo progetto.")

    if solution.is_approved:
        return jsonify({"message": "Soluzione già approvata."}), 200
    if task.status not in ['submitted', 'in_progress', 'open']:
        return jsonify({"error": f"Stato task non valido per approvazione ('{task.status}')."}), 400

    try:
        solution.is_approved = True
        task.status = 'approved' 
        
        collaborator = Collaborator.query.filter_by(
            project_id=task.project_id, 
            user_id=solution.submitted_by_user_id
        ).first()
        
        if collaborator:
            collaborator.equity_share = (collaborator.equity_share or 0.0) + task.equity_reward
        else:
            new_collaborator = Collaborator(
                project_id=task.project_id, 
                user_id=solution.submitted_by_user_id, 
                equity_share=task.equity_reward,
                role='collaborator'
            )
            db.session.add(new_collaborator)
            
        activity = Activity(
            user_id=current_user.id,
            action='approve_solution',
            project_id=project_id,
            task_id=task.id,
            solution_id=solution.id
        )
        db.session.add(activity)

        training_input = {
            "project_pitch": project.pitch,
            "project_description": project.description,
            "task_title": task.title,
            "task_description": task.description
        }
        training_output = {
            "approved_solution_content": solution.solution_content
        }
        
        new_training_data = TrainingData(
            source_project_id=project.id,
            source_task_id=task.id,
            source_solution_id=solution.id,
            input_data=training_input,
            output_data=training_output
        )
        db.session.add(new_training_data)

        # Notifica a tutti i collaboratori e al creatore
        from .models import Collaborator, Notification
        collaborator_ids = [c.user_id for c in Collaborator.query.filter_by(project_id=project.id).all()]
        if project.creator_id not in collaborator_ids:
            collaborator_ids.append(project.creator_id)
        for uid in set(collaborator_ids):
            notif = Notification(
                user_id=uid,
                project_id=project.id,
                type='solution_approved',
                message=f"La soluzione per il task '{task.title}' nel progetto '{project.name}' è stata approvata."
            )
            db.session.add(notif)

        db.session.commit()
        return jsonify({
            "message": "Soluzione approvata, equity assegnata e dati di training salvati!",
            "solution_id": solution.id,
            "task_status": task.status,
            "equity_assigned_to": solution.submitter.username,
            "equity_amount": task.equity_reward
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"API Errore Approvazione Soluzione: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server durante l'approvazione."}), 500


@api_solutions_bp.route('/solutions/<int:solution_id>/vote', methods=['POST'])
@login_required
def vote_solution_api(solution_id):
    solution = Solution.query.get_or_404(solution_id)
    task = solution.task
    project = task.project
    
    # Check if the user is a collaborator
    is_collaborator = Collaborator.query.filter_by(project_id=project.id, user_id=current_user.id).first()
    if not is_collaborator:
        return jsonify({"error": "Solo i collaboratori possono votare."}), 403

    # Check if the user has already voted on this task
    existing_vote = Vote.query.filter_by(user_id=current_user.id, task_id=task.id).first()
    if existing_vote:
        return jsonify({"error": "Hai già votato per una soluzione in questo task."}), 400

    new_vote = Vote(user_id=current_user.id, task_id=task.id, solution_id=solution.id)
    db.session.add(new_vote)
    
    # Check if the voting threshold has been met
    total_collaborators = Collaborator.query.filter_by(project_id=project.id).count()
    votes_on_task = Vote.query.filter_by(task_id=task.id).count()

    # Il creatore è sempre collaboratore, quindi è già incluso nel conteggio
    if total_collaborators > 0 and votes_on_task >= (total_collaborators // 2 + 1):
        # Calcola i voti per ciascuna soluzione
        solution_votes = db.session.query(
            Solution.id,
            func.count(Vote.id).label('total_votes')
        ).join(Vote).filter(Solution.task_id == task.id).group_by(Solution.id).all()

        # Trova la soluzione con più voti
        if solution_votes:
            max_votes = max(solution_votes, key=lambda sv: sv.total_votes).total_votes
            top_solutions = [sv for sv in solution_votes if sv.total_votes == max_votes]
            # Se c'è una sola soluzione con il massimo dei voti, accetta quella
            if len(top_solutions) == 1:
                winning_solution_id = top_solutions[0].id
                winning_solution = db.session.get(Solution, winning_solution_id)
                winning_solution.is_approved = True
                task.status = 'closed'

                # Assegna equity al vincitore
                winner_collaborator = Collaborator.query.filter_by(
                    project_id=project.id,
                    user_id=winning_solution.submitted_by_user_id
                ).first()
                if winner_collaborator:
                    winner_collaborator.equity_share = (winner_collaborator.equity_share or 0.0) + task.equity_reward
                else:
                    new_winner_collaborator = Collaborator(
                        project_id=project.id,
                        user_id=winning_solution.submitted_by_user_id,
                        equity_share=task.equity_reward,
                        role='collaborator'
                    )
                    db.session.add(new_winner_collaborator)
            # Se c'è ex aequo, annulla tutti i voti e si rivota
            elif len(top_solutions) > 1:
                Vote.query.filter_by(task_id=task.id).delete()
                db.session.commit()
                return jsonify({
                    "message": "Ex aequo tra soluzioni. Tutti i voti sono stati annullati, si prega di rivotare."
                }), 200

    try:
        db.session.commit()
        return jsonify({"message": "Voto registrato con successo!"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"API Errore Voto Soluzione: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server durante la registrazione del voto."}), 500


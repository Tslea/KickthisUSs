# app/api_free_proposals.py

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, current_app, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from .extensions import db, limiter
from .decorators import role_required
from .models import FreeProposal, Collaborator, Activity, Notification
from .services.equity_service import EquityService

api_free_proposals_bp = Blueprint('api_free_proposals', __name__)


def _parse_decision_payload():
    """Return normalized payload for free proposal decision."""
    data = request.get_json(silent=True)
    if data is None:
        data = request.form
    decision = (data.get('decision') or data.get('action') or '').strip().lower()
    note = (data.get('note') or data.get('decision_note') or '').strip()
    return decision, note


def _verify_proposal_context(project_id, proposal_id):
    """Load proposal ensuring it belongs to the project."""
    proposal = FreeProposal.query.options(
        joinedload(FreeProposal.project),
        joinedload(FreeProposal.developer),
        joinedload(FreeProposal.aggregated_tasks)
    ).get_or_404(proposal_id)

    if proposal.project_id != project_id:
        abort(404, description='Proposta non trovata per questo progetto.')

    return proposal


@api_free_proposals_bp.route(
    '/projects/<int:project_id>/free-proposals/<int:proposal_id>/decision',
    methods=['POST']
)
@login_required
@role_required('project_id', roles=['creator'])
@limiter.limit('50 per hour')
def handle_free_proposal_decision(project_id, proposal_id):
    """Accept or reject a free proposal via API."""
    proposal = _verify_proposal_context(project_id, proposal_id)

    if proposal.project.creator_id != current_user.id:
        abort(403, description='Solo il creatore del progetto può valutare questa proposta.')

    if not proposal.is_pending:
        return jsonify({
            "error": "Questa proposta è già stata valutata.",
            "status": proposal.status
        }), 409

    decision, decision_note = _parse_decision_payload()

    if decision not in {'accept', 'reject'}:
        return jsonify({"error": "Decisione non valida. Usa 'accept' o 'reject'."}), 400

    proposal.decision_note = decision_note
    proposal.decided_at = datetime.now(timezone.utc)

    if decision == 'accept':
        if not proposal.project.can_distribute_equity(proposal.equity_requested):
            available = proposal.project.get_available_equity()
            return jsonify({
                "error": f"Non c'è abbastanza equity disponibile ({available:.2f}%)."
            }), 400

        proposal.status = 'accepted'

        if proposal.proposal_type == 'multi_task':
            for task in proposal.aggregated_tasks:
                task.status = 'approved'
                setattr(task, 'assigned_to', proposal.developer_id)
                task_activity = Activity(
                    user_id=proposal.developer_id,
                    project_id=proposal.project_id,
                    task_id=task.id,
                    action=f'task_completato_proposta_libera: {task.title}'
                )
                db.session.add(task_activity)

        collaborator = Collaborator.query.filter_by(
            project_id=proposal.project_id,
            user_id=proposal.developer_id
        ).first()

        if not collaborator:
            collaborator = Collaborator(
                project_id=proposal.project_id,
                user_id=proposal.developer_id,
                role='developer',
                equity_share=0.0
            )
            db.session.add(collaborator)

        decision_activity = Activity(
            user_id=current_user.id,
            project_id=proposal.project_id,
            action=f'proposta_libera_accepted: {proposal.title}'
        )
        db.session.add(decision_activity)

        notification = Notification(
            user_id=proposal.developer_id,
            project_id=proposal.project_id,
            type='proposal_accepted',
            message=(
                f"🎉 La tua proposta '{proposal.title}' per {proposal.project.name} "
                f"è stata accettata! Hai guadagnato {proposal.equity_requested}% shares."
            )
        )
        db.session.add(notification)

        try:
            equity_service = EquityService()
            equity_service.distribute_free_proposal_equity(
                proposal,
                changed_by_user_id=current_user.id
            )
        except ValueError as equity_error:
            db.session.rollback()
            return jsonify({"error": str(equity_error)}), 400
        except Exception as error:
            db.session.rollback()
            current_app.logger.error(
                'Errore distribuzione equity per proposta libera %s: %s',
                proposal.id,
                error,
                exc_info=True
            )
            return jsonify({"error": "Errore interno durante la valutazione della proposta."}), 500

        response = {
            "message": (
                f"Proposta accettata. {proposal.developer.username} ha guadagnato "
                f"{proposal.equity_requested}% di shares."
            ),
            "status": proposal.status,
            "redirect_url": url_for('projects.project_detail', project_id=project_id)
        }
        return jsonify(response), 200

    # Decisione di rifiuto
    proposal.status = 'rejected'

    decision_activity = Activity(
        user_id=current_user.id,
        project_id=proposal.project_id,
        action=f'proposta_libera_rejected: {proposal.title}'
    )
    db.session.add(decision_activity)

    notification = Notification(
        user_id=proposal.developer_id,
        project_id=proposal.project_id,
        type='proposal_rejected',
        message=(
            f"La tua proposta '{proposal.title}' per {proposal.project.name} è stata rifiutata."
        )
    )
    db.session.add(notification)

    try:
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        current_app.logger.error(
            'Errore salvataggio rifiuto proposta libera %s: %s',
            proposal.id,
            error,
            exc_info=True
        )
        return jsonify({"error": "Errore interno durante la valutazione della proposta."}), 500

    response = {
        "message": "Proposta rifiutata.",
        "status": proposal.status,
        "redirect_url": url_for('projects.project_detail', project_id=project_id)
    }
    return jsonify(response), 200

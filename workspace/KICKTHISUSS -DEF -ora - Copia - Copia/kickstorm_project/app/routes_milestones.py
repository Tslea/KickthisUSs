# app/routes_milestones.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timezone
from .models import Milestone, Project, Collaborator
from .decorators import role_required
from .extensions import db
from .services.notification_service import NotificationService
from .utils import clean_plain_text_field, clean_rich_text_field

milestones_bp = Blueprint('milestones', __name__, template_folder='templates')


def check_milestone_access(project_id):
    """Verifica se l'utente può modificare le milestone del progetto"""
    project = Project.query.get_or_404(project_id)
    
    # Il creatore del progetto ha sempre accesso
    if project.creator_id == current_user.id:
        return True
    
    # Verifica se l'utente è un collaboratore del progetto
    collaborator = Collaborator.query.filter_by(
        project_id=project_id,
        user_id=current_user.id
    ).first()
    
    return collaborator is not None


@milestones_bp.route('/projects/<int:project_id>/milestones')
def milestones_list(project_id):
    """Visualizza la roadmap/milestone del progetto (visibile a tutti)"""
    project = Project.query.get_or_404(project_id)
    
    # Verifica accesso per progetti privati
    if project.private:
        if not current_user.is_authenticated:
            flash("Questo è un progetto privato. Devi effettuare il login per accedervi.", "warning")
            return redirect(url_for('auth.login'))
        
        is_creator = project.creator_id == current_user.id
        is_collaborator = Collaborator.query.filter_by(
            project_id=project.id, user_id=current_user.id
        ).first() is not None
        
        if not (is_creator or is_collaborator):
            flash("Non sei autorizzato ad accedere a questo progetto privato.", "error")
            return redirect(url_for('projects.projects_list'))
    
    # Ottieni tutte le milestone ordinate
    milestones = Milestone.query.filter_by(project_id=project_id).order_by(
        Milestone.display_order,
        Milestone.created_at
    ).all()
    
    # Verifica se l'utente può modificare
    can_edit = False
    if current_user.is_authenticated:
        can_edit = check_milestone_access(project_id)
    
    return render_template('milestones/index.html', 
                         project=project, 
                         milestones=milestones,
                         can_edit=can_edit)


@milestones_bp.route('/projects/<int:project_id>/milestones/new', methods=['GET', 'POST'])
@login_required
def create_milestone(project_id):
    """Crea una nuova milestone (solo creatore e collaboratori)"""
    if not check_milestone_access(project_id):
        flash('Non hai i permessi per creare milestone in questo progetto.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        target_date_str = request.form.get('target_date', '').strip()
        display_order = request.form.get('display_order', type=int) or 0
        
        try:
            cleaned_title = clean_plain_text_field('milestone', 'title', title)
            cleaned_description = clean_rich_text_field('milestone', 'description', description)
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('milestones/create.html', project=project)
        
        # Parse target_date
        target_date = None
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato data non valido. Usa YYYY-MM-DD.', 'error')
                return render_template('milestones/create.html', project=project)
        
        # Crea la milestone
        milestone = Milestone(
            project_id=project_id,
            title=cleaned_title,
            description=cleaned_description or None,
            target_date=target_date,
            display_order=display_order,
            created_by=current_user.id
        )
        
        db.session.add(milestone)
        
        # Notifica i collaboratori
        NotificationService.notify_milestone_created(project, title, current_user.id)
        
        db.session.commit()
        
        flash('Milestone creata con successo!', 'success')
        return redirect(url_for('milestones.milestones_list', project_id=project_id))
    
    return render_template('milestones/create.html', project=project)


@milestones_bp.route('/projects/<int:project_id>/milestones/<int:milestone_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_milestone(project_id, milestone_id):
    """Modifica una milestone (solo creatore e collaboratori)"""
    if not check_milestone_access(project_id):
        flash('Non hai i permessi per modificare milestone in questo progetto.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    milestone = Milestone.query.filter_by(
        project_id=project_id,
        id=milestone_id
    ).first_or_404()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        target_date_str = request.form.get('target_date', '').strip()
        display_order = request.form.get('display_order', type=int) or 0
        
        try:
            cleaned_title = clean_plain_text_field('milestone', 'title', title)
            cleaned_description = clean_rich_text_field('milestone', 'description', description)
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template('milestones/edit.html', project=project, milestone=milestone)
        
        # Parse target_date
        target_date = None
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato data non valido. Usa YYYY-MM-DD.', 'error')
                return render_template('milestones/edit.html', project=project, milestone=milestone)
        
        # Aggiorna la milestone
        milestone.title = cleaned_title
        milestone.description = cleaned_description or None
        milestone.target_date = target_date
        milestone.display_order = display_order
        milestone.updated_at = datetime.now(timezone.utc)
        
        # Notifica i collaboratori
        NotificationService.notify_milestone_updated(project, title, current_user.id)
        
        db.session.commit()
        
        flash('Milestone aggiornata con successo!', 'success')
        return redirect(url_for('milestones.milestones_list', project_id=project_id))
    
    return render_template('milestones/edit.html', project=project, milestone=milestone)


@milestones_bp.route('/projects/<int:project_id>/milestones/<int:milestone_id>/toggle', methods=['POST'])
@login_required
def toggle_milestone(project_id, milestone_id):
    """Marca/rimuove il completamento di una milestone (solo creatore e collaboratori)"""
    if not check_milestone_access(project_id):
        return jsonify({'success': False, 'message': 'Non hai i permessi per modificare questa milestone.'}), 403
    
    project = Project.query.get_or_404(project_id)
    milestone = Milestone.query.filter_by(
        project_id=project_id,
        id=milestone_id
    ).first_or_404()
    
    if milestone.completed:
        milestone.mark_incomplete()
        message = f"Milestone '{milestone.title}' segnata come non completata."
    else:
        milestone.mark_completed(current_user.id)
        message = f"Milestone '{milestone.title}' completata!"
        # Notifica i collaboratori
        NotificationService.notify_milestone_completed(project, milestone.title, current_user.id)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': message,
        'completed': milestone.completed,
        'completed_at': milestone.completed_at.isoformat() if milestone.completed_at else None
    })


@milestones_bp.route('/projects/<int:project_id>/milestones/<int:milestone_id>/delete', methods=['POST'])
@login_required
def delete_milestone(project_id, milestone_id):
    """Elimina una milestone (solo creatore e collaboratori)"""
    if not check_milestone_access(project_id):
        flash('Non hai i permessi per eliminare milestone in questo progetto.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    milestone = Milestone.query.filter_by(
        project_id=project_id,
        id=milestone_id
    ).first_or_404()
    
    title = milestone.title
    db.session.delete(milestone)
    db.session.commit()
    
    flash(f'Milestone "{title}" eliminata con successo.', 'success')
    return redirect(url_for('milestones.milestones_list', project_id=project_id))


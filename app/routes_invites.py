import uuid
import secrets
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import Project, ProjectInvite, User, Collaborator, Notification
from .decorators import role_required

invites_bp = Blueprint('invites', __name__, template_folder='templates')

@invites_bp.route('/project/<int:project_id>/invites')
@login_required
def manage_project_invites(project_id):
    """Pagina di gestione degli inviti del progetto."""
    project = Project.query.get_or_404(project_id)
    
    # Controlla se l'utente è autorizzato a gestire gli inviti
    is_creator = project.creator_id == current_user.id
    is_collaborator = Collaborator.query.filter_by(
        project_id=project.id, user_id=current_user.id
    ).first() is not None
    
    if not (is_creator or is_collaborator):
        flash("Non sei autorizzato a gestire gli inviti per questo progetto.", "error")
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    # Ottieni tutti gli inviti pendenti
    pending_invites = ProjectInvite.query.filter_by(
        project_id=project_id
    ).all()
    
    return render_template(
        'project_invites.html',
        project=project,
        pending_invites=pending_invites,
        is_creator=is_creator,
        is_collaborator=is_collaborator
    )

@invites_bp.route('/project/<int:project_id>/send-invite', methods=['POST'])
@login_required
def send_project_invite(project_id):
    """Invia un invito a un utente per unirsi al progetto."""
    project = Project.query.get_or_404(project_id)
    
    # Solo il creatore o i collaboratori possono inviare inviti
    is_creator = project.creator_id == current_user.id
    is_collaborator = Collaborator.query.filter_by(
        project_id=project.id, user_id=current_user.id
    ).first() is not None
    
    if not (is_creator or is_collaborator):
        flash("Non sei autorizzato a inviare inviti per questo progetto.", "error")
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    email = request.form.get('email')
    if not email:
        flash("Inserisci un'email valida.", "error")
        return redirect(url_for('invites.manage_project_invites', project_id=project_id))
    
    # Controlla se l'utente esiste
    invitee = User.query.filter_by(email=email).first()
    if not invitee:
        flash("Non è stato trovato un utente con questa email.", "error")
        return redirect(url_for('invites.manage_project_invites', project_id=project_id))
    
    # Controlla se l'utente è già un collaboratore
    existing_collab = Collaborator.query.filter_by(
        project_id=project_id, user_id=invitee.id
    ).first()
    if existing_collab:
        flash("Questo utente è già un collaboratore del progetto.", "warning")
        return redirect(url_for('invites.manage_project_invites', project_id=project_id))
    
    # Controlla se esiste già un invito pendente
    existing_invite = ProjectInvite.query.filter_by(
        project_id=project_id, invitee_id=invitee.id, status='pending'
    ).first()
    if existing_invite:
        flash("Esiste già un invito pendente per questo utente.", "warning")
        return redirect(url_for('invites.manage_project_invites', project_id=project_id))
    
    # Crea il nuovo invito
    invite_token = secrets.token_urlsafe(32)
    new_invite = ProjectInvite(
        project_id=project_id,
        inviter_id=current_user.id,
        invitee_id=invitee.id,
        invite_token=invite_token,
        status='pending'
    )
    
    # Crea una notifica per l'invitato
    notification = Notification(
        user_id=invitee.id,
        project_id=project_id,
        type='project_invite',
        message=f"{current_user.username} ti ha invitato a collaborare al progetto '{project.name}'."
    )
    
    try:
        db.session.add(new_invite)
        db.session.add(notification)
        db.session.commit()
        flash("Invito inviato con successo.", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Si è verificato un errore nell'invio dell'invito.", "error")
    
    return redirect(url_for('invites.manage_project_invites', project_id=project_id))

@invites_bp.route('/project/<int:project_id>/invite/<int:invite_id>/cancel', methods=['POST'])
@login_required
def cancel_project_invite(project_id, invite_id):
    """Annulla un invito pendente."""
    project = Project.query.get_or_404(project_id)
    
    # Solo il creatore può annullare gli inviti
    if project.creator_id != current_user.id:
        flash("Solo il creatore del progetto può annullare gli inviti.", "error")
        return redirect(url_for('invites.manage_project_invites', project_id=project_id))
    
    invite = ProjectInvite.query.get_or_404(invite_id)
    if invite.project_id != project_id:
        abort(404)
    
    if invite.status != 'pending':
        flash("Puoi annullare solo gli inviti pendenti.", "warning")
        return redirect(url_for('invites.manage_project_invites', project_id=project_id))
    
    # Aggiorna lo stato dell'invito
    invite.status = 'cancelled'
    
    # Crea una notifica per l'invitato
    notification = Notification(
        user_id=invite.invitee_id,
        project_id=project_id,
        type='project_invite_cancelled',
        message=f"L'invito al progetto '{project.name}' è stato annullato."
    )
    
    try:
        db.session.add(notification)
        db.session.commit()
        flash("Invito annullato con successo.", "success")
    except:
        db.session.rollback()
        flash("Si è verificato un errore nell'annullamento dell'invito.", "error")
    
    return redirect(url_for('invites.manage_project_invites', project_id=project_id))

@invites_bp.route('/invite/<string:token>/accept')
@login_required
def accept_project_invite(token):
    """Accetta un invito di progetto."""
    invite = ProjectInvite.query.filter_by(invite_token=token, status='pending').first_or_404()
    
    # Verifica che l'utente loggato sia l'invitato
    if invite.invitee_id != current_user.id:
        flash("Non sei autorizzato ad accettare questo invito.", "error")
        return redirect(url_for('projects.home'))
    
    # Aggiorna lo stato dell'invito
    invite.status = 'accepted'
    
    # Aggiungi l'utente come collaboratore
    new_collab = Collaborator(
        project_id=invite.project_id,
        user_id=current_user.id,
        role='collaborator',
        equity_share=0  # L'equity iniziale è 0, può essere modificata in seguito
    )
    
    # Crea una notifica per il creatore del progetto
    notification = Notification(
        user_id=invite.project.creator_id,
        project_id=invite.project_id,
        type='project_invite_accepted',
        message=f"{current_user.username} ha accettato l'invito a collaborare al progetto '{invite.project.name}'."
    )
    
    try:
        db.session.add(new_collab)
        db.session.add(notification)
        db.session.commit()
        flash("Hai accettato l'invito con successo. Ora sei un collaboratore del progetto!", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Si è verificato un errore nell'accettazione dell'invito.", "error")
    
    return redirect(url_for('projects.project_detail', project_id=invite.project_id))

@invites_bp.route('/invite/<string:token>/decline')
@login_required
def decline_project_invite(token):
    """Rifiuta un invito di progetto."""
    invite = ProjectInvite.query.filter_by(invite_token=token, status='pending').first_or_404()
    
    # Verifica che l'utente loggato sia l'invitato
    if invite.invitee_id != current_user.id:
        flash("Non sei autorizzato a rifiutare questo invito.", "error")
        return redirect(url_for('projects.home'))
    
    # Aggiorna lo stato dell'invito
    invite.status = 'declined'
    
    # Crea una notifica per il creatore del progetto
    notification = Notification(
        user_id=invite.project.creator_id,
        project_id=invite.project_id,
        type='project_invite_declined',
        message=f"{current_user.username} ha rifiutato l'invito a collaborare al progetto '{invite.project.name}'."
    )
    
    try:
        db.session.add(notification)
        db.session.commit()
        flash("Hai rifiutato l'invito con successo.", "info")
    except:
        db.session.rollback()
        flash("Si è verificato un errore nel rifiuto dell'invito.", "error")
    
    return redirect(url_for('projects.home'))

@invites_bp.route('/project/<int:project_id>/toggle-visibility', methods=['POST'])
@login_required
def toggle_project_visibility(project_id):
    """Cambia la visibilità di un progetto da privato a pubblico."""
    project = Project.query.get_or_404(project_id)
    
    # Solo il creatore può cambiare la visibilità
    if project.creator_id != current_user.id:
        flash("Solo il creatore può modificare la visibilità del progetto.", "error")
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    # Se è già pubblico, non fare nulla
    if not project.private:
        flash("Questo progetto è già pubblico.", "info")
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    # Rendi il progetto pubblico
    project.private = False
    
    try:
        db.session.commit()
        flash("Il progetto è stato reso pubblico con successo.", "success")
    except:
        db.session.rollback()
        flash("Si è verificato un errore nel rendere pubblico il progetto.", "error")
    
    return redirect(url_for('projects.project_detail', project_id=project_id))



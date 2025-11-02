# app/routes_free_proposals.py

from datetime import datetime, timezone
import os
from typing import List

from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from .extensions import db
from .models import (
    Project, Task, FreeProposal, FreeProposalFile, Notification,
    Collaborator, Activity, CONTENT_TYPES
)
from .decorators import role_required
from .routes_tasks import allowed_file, allowed_hardware_file, get_file_type

free_proposals_bp = Blueprint('free_proposals', __name__, template_folder='templates')


def create_notification(user_id, notification_type, message, project_id=None):
    """Helper per creare notifiche"""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        message=message,
        project_id=project_id
    )
    db.session.add(notification)
    return notification


def _get_upload_folder() -> str:
    """Restituisce (e crea se necessario) la cartella upload per le proposte libere."""
    upload_root = current_app.config.get('UPLOAD_FOLDER', 'instance/uploads')
    if not os.path.isabs(upload_root):
        upload_root = os.path.join(current_app.instance_path, upload_root)

    proposal_folder = os.path.join(upload_root, 'free_proposals')
    os.makedirs(proposal_folder, exist_ok=True)
    return proposal_folder


def _save_proposal_files(proposal_id: int, files: list, upload_folder: str, content_type: str) -> List[FreeProposalFile]:
    """Persisti i file caricati per una proposta libera."""
    saved_files: list[FreeProposalFile] = []

    if not files:
        return saved_files

    for file in files:
        if not file or not file.filename:
            continue

        filename = file.filename.strip()
        is_allowed = allowed_file(filename) or allowed_hardware_file(filename)
        if not is_allowed:
            raise ValueError(f"Tipo di file non supportato: {filename}")

        safe_name = secure_filename(f"{proposal_id}_{datetime.now(timezone.utc).timestamp()}_{filename}")
        storage_path = os.path.join(upload_folder, safe_name)
        file.save(storage_path)

        try:
            relative_path = os.path.relpath(storage_path, current_app.instance_path)
        except ValueError:
            # In rari casi su Windows relpath può fallire per drive diversi: fallback al basename
            relative_path = os.path.join(os.path.basename(upload_folder), safe_name)

        proposal_file = FreeProposalFile(
            proposal_id=proposal_id,
            original_filename=filename,
            stored_filename=safe_name,
            file_path=relative_path.replace('\\', '/'),
            file_type=get_file_type(filename),
            content_type=content_type,
            file_size=os.path.getsize(storage_path),
            mime_type=file.content_type or 'application/octet-stream'
        )
        saved_files.append(proposal_file)

    return saved_files


@free_proposals_bp.route('/project/<int:project_id>/propose-free', methods=['GET', 'POST'])
@login_required
def propose_free_solution(project_id):
    """
    Proponi una soluzione libera (aggregazione multi-task o nuovo task)
    
    UI/UX Best Practices:
    - Form chiaro e intuitivo con sezioni ben separate
    - Preview dell'equity totale in tempo reale
    - Validazione client-side e server-side
    - Feedback visivo per ogni azione
    """
    project = Project.query.get_or_404(project_id)
    
    # Validazione: non puoi proporre soluzioni al tuo progetto
    if project.creator_id == current_user.id:
        flash('❌ Non puoi proporre soluzioni al tuo progetto', 'warning')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    # Validazione: il progetto deve essere attivo
    if project.status != 'open':
        flash('❌ Questo progetto non accetta più proposte', 'warning')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    if request.method == 'POST':
        try:
            proposal_type = request.form.get('proposal_type')
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            equity_requested = float(request.form.get('equity_requested', 0))
            content_type = request.form.get('content_type', 'software')
            implementation_details = request.form.get('solution_content', '').strip()
            solution_code_auto = request.form.get('solution_code_auto', '').strip()
            pull_request_url = request.form.get('pull_request_url', '').strip()
            uploaded_files = request.files.getlist('files')
            
            # Validazione base
            if not title or not description:
                flash('❌ Titolo e descrizione sono obbligatori', 'danger')
                return redirect(request.url)
            
            if len(title) < 5 or len(title) > 200:
                flash('❌ Il titolo deve essere tra 5 e 200 caratteri', 'danger')
                return redirect(request.url)
            
            if len(description) < 50:
                flash('❌ La descrizione deve essere di almeno 50 caratteri per essere significativa', 'danger')
                return redirect(request.url)
            
            # Validazione equity
            if equity_requested <= 0 or equity_requested > 100:
                flash('❌ L\'equity richiesta deve essere tra 0.1% e 100%', 'danger')
                return redirect(request.url)
            
            # Controllo equity disponibile nel progetto
            available_equity = project.get_available_equity()
            if equity_requested > available_equity:
                flash(f'❌ L\'equity richiesta ({equity_requested}%) supera quella disponibile ({available_equity:.2f}%)', 'danger')
                return redirect(request.url)

            if content_type not in CONTENT_TYPES:
                flash('❌ Tipo di contenuto non valido per la proposta.', 'danger')
                return redirect(request.url)

            publish_method = 'auto' if solution_code_auto else 'manual'
            
            # Crea la proposta
            proposal = FreeProposal(
                project_id=project_id,
                developer_id=current_user.id,
                title=title,
                description=description,
                equity_requested=equity_requested,
                proposal_type=proposal_type,
                status='pending',
                content_type=content_type,
                publish_method=publish_method,
                implementation_details=implementation_details or None
            )
            
            if proposal_type == 'multi_task':
                # Aggrega task esistenti
                task_ids = request.form.getlist('task_ids')
                
                if not task_ids:
                    flash('❌ Seleziona almeno un task da aggregare', 'danger')
                    return redirect(request.url)
                
                # Verifica che i task esistano e siano aperti
                tasks = Task.query.filter(
                    Task.id.in_(task_ids),
                    Task.project_id == project_id,
                    Task.status == 'open'
                ).all()
                
                if len(tasks) != len(task_ids):
                    flash('❌ Alcuni task selezionati non sono validi o non sono più aperti', 'danger')
                    return redirect(request.url)
                
                proposal.aggregated_tasks = tasks
                
                # Log per debug
                current_app.logger.info(f"Proposta multi-task creata: {len(tasks)} task aggregati")
                
            elif proposal_type == 'new_task':
                # Nuovo task proposto
                new_task_details = request.form.get('new_task_details', '').strip()
                
                if not new_task_details or len(new_task_details) < 50:
                    flash('❌ La descrizione del nuovo task deve essere di almeno 50 caratteri', 'danger')
                    return redirect(request.url)
                
                proposal.new_task_details = new_task_details
                
                current_app.logger.info(f"Proposta nuovo task creata: {title}")
            
            else:
                flash('❌ Tipo di proposta non valido', 'danger')
                return redirect(request.url)
            
            db.session.add(proposal)
            db.session.flush()  # Per ottenere l'ID della proposta

            # Gestione salvataggio file allegati
            saved_files = []
            if uploaded_files:
                try:
                    upload_folder = _get_upload_folder()
                    saved_files = _save_proposal_files(proposal.id, uploaded_files, upload_folder, content_type)
                except ValueError as file_error:
                    db.session.rollback()
                    flash(str(file_error), 'danger')
                    return redirect(request.url)

                for proposal_file in saved_files:
                    db.session.add(proposal_file)

                if saved_files and not proposal.primary_file_path:
                    proposal.primary_file_path = saved_files[0].file_path

            auto_pr_created = False

            if solution_code_auto and project.github_repo_name:
                try:
                    from services.github_auto_publisher import GitHubAutoPublisher, extract_code_from_textarea

                    publisher = GitHubAutoPublisher()
                    content_data = extract_code_from_textarea(solution_code_auto, content_type)

                    task_info = {
                        'task_id': f"proposal-{proposal.id}",
                        'title': title,
                        'description': description or ''
                    }

                    user_info = {
                        'username': current_user.username,
                        'email': current_user.email,
                        'github_username': getattr(current_user, 'github_username', None)
                    }

                    repo_url = f"https://github.com/{project.github_repo_name}"
                    result = publisher.publish_solution_auto(
                        repo_url=repo_url,
                        content_data=content_data,
                        task_info=task_info,
                        user_info=user_info
                    )

                    if result['success']:
                        proposal.github_pr_url = result['pr_url']
                        proposal.github_pr_number = result.get('pr_number')
                        proposal.github_branch_name = result.get('branch_name')
                        auto_pr_created = True
                        flash(f"✨ Pull Request creata automaticamente! {proposal.github_pr_url}", 'success')
                    else:
                        raise ValueError(result.get('error', 'Errore durante la creazione automatica della PR'))

                except Exception as auto_error:
                    db.session.rollback()
                    current_app.logger.error("Errore creazione auto-PR per proposta libera", exc_info=True)
                    flash(f"❌ Creazione automatica della PR fallita: {auto_error}", 'danger')
                    return redirect(request.url)
            elif pull_request_url:
                proposal.github_pr_url = pull_request_url
            
            # Crea notifica per il creatore del progetto
            create_notification(
                user_id=project.creator_id,
                notification_type='free_proposal',
                message=f'🚀 {current_user.username} ha proposto una soluzione libera per {project.name}',
                project_id=project_id
            )
            
            # Log attività
            activity = Activity(
                user_id=current_user.id,
                project_id=project_id,
                action=f'proposta_libera_creata: {title} ({content_type})'
            )
            db.session.add(activity)
            
            db.session.commit()
            
            flash('✅ Proposta inviata con successo! Il creatore del progetto la valuterà presto. 🚀', 'success')
            return redirect(url_for('free_proposals.view_free_proposal', proposal_id=proposal.id))
            
        except ValueError as e:
            flash('❌ Errore nei dati inseriti. Controlla che l\'equity sia un numero valido.', 'danger')
            current_app.logger.error(f"Errore validazione proposta: {e}")
            return redirect(request.url)
        except Exception as e:
            db.session.rollback()
            flash('❌ Errore durante la creazione della proposta. Riprova.', 'danger')
            current_app.logger.error(f"Errore creazione proposta: {e}")
            return redirect(request.url)
    
    # GET: mostra form
    available_tasks = Task.query.filter_by(
        project_id=project_id,
        status='open'
    ).all()
    
    # Calcola equity disponibile
    available_equity = project.get_available_equity()
    
    return render_template('free_proposals/propose_free_solution.html',
                         project=project,
                         available_tasks=available_tasks,
                         available_equity=available_equity)


@free_proposals_bp.route('/proposal/<int:proposal_id>')
@login_required
def view_free_proposal(proposal_id):
    """
    Visualizza dettagli di una proposta libera
    
    Access Control:
    - Creatore del progetto: può vedere e decidere
    - Proponente: può vedere
    - Altri utenti: solo se è pubblica
    """
    proposal = FreeProposal.query.get_or_404(proposal_id)
    
    # Controllo accesso
    is_creator = current_user.id == proposal.project.creator_id
    is_developer = current_user.id == proposal.developer_id
    
    if not is_creator and not is_developer:
        if not proposal.is_public:
            abort(403)
    
    # Carica i task aggregati se multi-task
    aggregated_tasks = []
    if proposal.proposal_type == 'multi_task':
        aggregated_tasks = proposal.aggregated_tasks
    
    return render_template('free_proposals/view_free_proposal.html',
                         proposal=proposal,
                         aggregated_tasks=aggregated_tasks,
                         is_creator=is_creator,
                         is_developer=is_developer)


@free_proposals_bp.route('/proposal/<int:proposal_id>/delete', methods=['POST'])
@login_required
def delete_free_proposal(proposal_id):
    """
    Elimina una proposta libera (solo se pending e solo dal proponente)
    """
    proposal = FreeProposal.query.get_or_404(proposal_id)
    
    # Solo il proponente può eliminare la propria proposta
    if proposal.developer_id != current_user.id:
        abort(403)
    
    # Solo se è ancora pending
    if proposal.status != 'pending':
        flash('❌ Non puoi eliminare una proposta già valutata', 'warning')
        return redirect(url_for('free_proposals.view_free_proposal', proposal_id=proposal_id))
    
    try:
        project_id = proposal.project_id
        db.session.delete(proposal)
        db.session.commit()
        
        flash('✅ Proposta eliminata con successo', 'success')
        return redirect(url_for('projects.project_detail', project_id=project_id))
        
    except Exception as e:
        db.session.rollback()
        flash('❌ Errore durante l\'eliminazione della proposta', 'danger')
        current_app.logger.error(f"Errore eliminazione proposta: {e}")
        return redirect(url_for('free_proposals.view_free_proposal', proposal_id=proposal_id))


@free_proposals_bp.route('/my-proposals')
@login_required
def my_proposals():
    """
    Dashboard delle mie proposte libere (inviate e ricevute)
    """
    # Proposte inviate
    submitted_proposals = FreeProposal.query.filter_by(
        developer_id=current_user.id
    ).order_by(FreeProposal.created_at.desc()).all()
    
    # Proposte ricevute (per i progetti che gestisco come creator o collaboratore)
    my_projects = Project.query.filter_by(creator_id=current_user.id).all()
    project_ids = [p.id for p in my_projects]

    collaborator_projects = Collaborator.query.filter_by(user_id=current_user.id).all()
    collaborator_ids = [c.project_id for c in collaborator_projects]

    managed_project_ids = list({*project_ids, *collaborator_ids})

    if managed_project_ids:
        received_proposals = FreeProposal.query.filter(
            FreeProposal.project_id.in_(managed_project_ids)
        ).order_by(FreeProposal.created_at.desc()).all()
    else:
        received_proposals = []
    
    return render_template('free_proposals/my_proposals.html',
                         submitted_proposals=submitted_proposals,
                         received_proposals=received_proposals)

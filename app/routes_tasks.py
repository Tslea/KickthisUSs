# app/routes_tasks.py

from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, current_app, Response, jsonify
from sqlalchemy.orm import joinedload
from flask_login import login_required, current_user
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
import os

from .extensions import db
from .models import (
    Project, Task, Solution, SolutionFile, Activity,
    ALLOWED_TASK_PHASES, ALLOWED_TASK_STATUS, ALLOWED_TASK_DIFFICULTIES
)
from .forms import SolutionForm, AddTaskForm, BaseForm
from .decorators import role_required
from .ai_services import generate_suggested_tasks, analyze_solution_content

tasks_bp = Blueprint('tasks', __name__, template_folder='templates')
MAX_SOLUTIONS_PER_USER = 3
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'txt', 'pdf', 'zip', 'rar'}

# Estensioni specifiche per flusso hardware
HARDWARE_FILE_TYPES = {
    'source': {'step', 'stp', 'dwg', 'sch', 'brd', 'kicad_pcb', 'pro', 'lib'},
    'prototype': {'stl', '3mf', 'gcode', 'svg', 'dxf'},
    'documentation': {'pdf', 'docx', 'doc', 'md', 'txt', 'odt'},
    'visual': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'mp4', 'webm', 'avi', 'mov'}
}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename: str) -> str:
    """Determina il tipo di file hardware basato sull'estensione"""
    if '.' not in filename:
        return 'documentation'
    
    ext = filename.rsplit('.', 1)[1].lower()
    for file_type, extensions in HARDWARE_FILE_TYPES.items():
        if ext in extensions:
            return file_type
    return 'documentation'  # Default

def allowed_hardware_file(filename: str) -> bool:
    """Verifica se il file è supportato per il flusso hardware"""
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    for extensions in HARDWARE_FILE_TYPES.values():
        if ext in extensions:
            return True
    return False

def save_solution_files(files_dict: dict, solution_id: int, upload_folder: str) -> list:
    """Salva file multipli per una soluzione e restituisce lista di SolutionFile objects"""
    saved_files = []
    
    for field_name, files in files_dict.items():
        if not files:
            continue
            
        if not isinstance(files, list):
            files = [files]
        
        for file in files:
            if file and file.filename and allowed_hardware_file(file.filename):
                filename = secure_filename(f"{solution_id}_{timezone.now().timestamp()}_{file.filename}")
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                file_type = get_file_type(file.filename)
                
                solution_file = SolutionFile(
                    solution_id=solution_id,
                    original_filename=file.filename,
                    stored_filename=filename,
                    file_path=os.path.join(os.path.basename(upload_folder), filename),
                    file_type=file_type,
                    file_size=os.path.getsize(file_path),
                    mime_type=file.content_type or 'application/octet-stream'
                )
                saved_files.append(solution_file)
    
    return saved_files

@tasks_bp.route('/project/<int:project_id>/add_task', methods=['GET', 'POST'])
@login_required
def add_task_form(project_id: int) -> Response | str:
    project = Project.query.get_or_404(project_id)
    
    # Verifica se l'utente può aggiungere task (creatore o collaboratore)
    from .models import Collaborator
    from sqlalchemy import and_
    
    is_creator = project.creator_id == current_user.id
    is_collaborator = db.session.query(Collaborator).filter(
        and_(Collaborator.project_id == project.id,
             Collaborator.user_id == current_user.id)
    ).first() is not None
    
    if not (is_creator or is_collaborator):
        abort(403)

    form = AddTaskForm()
    if form.validate_on_submit():
        # Se l'utente tenta di creare un task privato, verifica i permessi
        if form.is_private.data and not (is_creator or is_collaborator):
            flash('Non puoi creare task privati per questo progetto.', 'danger')
            return redirect(url_for('projects.project_detail', project_id=project.id))
            
        new_task = Task(
            project_id=project.id,
            creator_id=current_user.id,
            title=form.title.data,
            description=form.description.data,
            task_type=form.task_type.data,
            phase=form.phase.data,
            difficulty=form.difficulty.data,
            equity_reward=form.equity_reward.data,
            is_private=form.is_private.data,
            status='open'
        )
        
        # Se è un esperimento di validazione, aggiungi i campi specifici
        if form.task_type.data == 'validation':
            new_task.hypothesis = form.hypothesis.data if hasattr(form, 'hypothesis') else None
            new_task.test_method = form.test_method.data if hasattr(form, 'test_method') else None
        
        db.session.add(new_task)
        db.session.flush()
        
        # Notifica solo alle persone che possono vedere il task
        from .models import Collaborator, Notification
        notification_recipient_ids = []
        
        if new_task.is_private:
            # Per task privati, notifica solo creatore progetto e collaboratori
            collaborator_ids = [c.user_id for c in Collaborator.query.filter_by(project_id=project.id).all()]
            if project.creator_id not in collaborator_ids:
                collaborator_ids.append(project.creator_id)
            notification_recipient_ids = collaborator_ids
        else:
            # Per task pubblici, notifica a tutti i collaboratori e al creatore
            collaborator_ids = [c.user_id for c in Collaborator.query.filter_by(project_id=project.id).all()]
            if project.creator_id not in collaborator_ids:
                collaborator_ids.append(project.creator_id)
            notification_recipient_ids = collaborator_ids
        
        # Crea le notifiche
        task_type_text = "privato" if new_task.is_private else "pubblico"
        for uid in set(notification_recipient_ids):
            if uid != current_user.id:
                notif = Notification(
                    user_id=uid,
                    project_id=project.id,
                    type='task_created',
                    message=f"È stato creato un nuovo task {task_type_text} '{new_task.title}' nel progetto '{project.name}'."
                )
                db.session.add(notif)
        db.session.commit()
        flash('Task aggiunto con successo!', 'success')
        return redirect(url_for('projects.project_detail', project_id=project.id))

    return render_template('add_task.html', project=project, form=form)

# --- ROUTE API PER SUGGERIRE UN TASK (CORRETTA) ---
@tasks_bp.route('/project/<int:project_id>/suggest-ai-task', methods=['POST'])
def suggest_ai_task_api(project_id: int):
    # Controllo manuale dell'autenticazione per garantire una risposta JSON
    if not current_user.is_authenticated:
        return jsonify({'error': 'Autenticazione richiesta per questa operazione.'}), 401

    project = db.session.get(Project, project_id)
    if not project:
        return jsonify({'error': 'Progetto non trovato.'}), 404

    # Solo il creatore del progetto può aggiungere task suggeriti
    if project.creator_id != current_user.id:
        return jsonify({'error': 'Non autorizzato a eseguire questa azione.'}), 403

    try:
        suggested_tasks = generate_suggested_tasks(
            pitch=project.pitch,
            category=project.category,
            description=project.description
        )
        if not suggested_tasks:
            return jsonify({'error': "L'IA non è riuscita a generare un task al momento. Riprova."}), 500
        
        task_data = suggested_tasks[0]

        new_task = Task(
            project_id=project.id,
            creator_id=current_user.id,
            title=task_data.get('title', 'Task senza titolo'),
            description=task_data.get('description', ''),
            task_type=task_data.get('task_type', 'proposal'),
            phase=task_data.get('phase', 'Planning'),
            difficulty=task_data.get('difficulty', 'Medium'),
            equity_reward=task_data.get('equity_reward', 0.1),
            status='suggested',
            is_suggestion=True
        )
        
        # Se è un esperimento di validazione, aggiungi i campi specifici
        if task_data.get('task_type') == 'validation':
            new_task.hypothesis = task_data.get('hypothesis', '')
            new_task.test_method = task_data.get('test_method', '')
            new_task.results = task_data.get('results', '')
        
        db.session.add(new_task)
        db.session.commit()
        
        return jsonify({
            'id': new_task.id,
            'title': new_task.title,
            'description': new_task.description,
            'task_type': new_task.task_type,
            'phase': new_task.phase,
            'difficulty': new_task.difficulty,
            'equity_reward': new_task.equity_reward,
            'status': new_task.status,
            'creator_id': new_task.creator_id,
            'creator_username': new_task.creator.username,
            'phase_display': ALLOWED_TASK_PHASES.get(new_task.phase),
            'difficulty_display': ALLOWED_TASK_DIFFICULTIES.get(new_task.difficulty),
            'status_display': ALLOWED_TASK_STATUS.get(new_task.status)
        })
    except Exception as e:
        current_app.logger.error(f"Errore durante la generazione del task AI: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@tasks_bp.route('/task/<int:task_id>/update_results', methods=['POST'])
@login_required
def update_task_results(task_id: int):
    """Aggiorna i risultati di un esperimento di validazione"""
    task = Task.query.get_or_404(task_id)
    
    # Verifica che sia un esperimento di validazione
    if task.task_type != 'validation':
        flash("Questa funzione è disponibile solo per gli esperimenti di validazione.", "error")
        return redirect(url_for('tasks.task_detail', task_id=task_id))
    
    # Verifica i permessi
    if task.creator_id != current_user.id:
        flash("Non hai il permesso di aggiornare i risultati di questo task.", "error")
        return redirect(url_for('tasks.task_detail', task_id=task_id))
    
    results = request.form.get('results', '').strip()
    if results:
        task.results = results
        
        # Se vengono inseriti i risultati, aggiorna lo status
        if task.status == 'open':
            task.status = 'in_progress'
        elif task.status == 'in_progress' and results:
            task.status = 'submitted'  # Pronto per la revisione
        
        db.session.commit()
        flash("Risultati aggiornati con successo!", "success")
    else:
        flash("I risultati non possono essere vuoti.", "error")
    
    return redirect(url_for('tasks.task_detail', task_id=task_id))


# --- NUOVA ROUTE PER ELIMINARE UN TASK ---
@tasks_bp.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id: int):
    task = Task.query.get_or_404(task_id)
    
    if task.creator_id != current_user.id:
        flash("Non hai il permesso di eliminare questo task.", "danger")
        abort(403)

    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()

    flash("Task eliminato con successo.", "success")
    return redirect(url_for('projects.project_detail', project_id=project_id))


@tasks_bp.route('/task/<int:task_id>')
def task_detail(task_id: int) -> Response | str:
    task: Task = Task.query.options(joinedload(Task.project), joinedload(Task.creator)).get_or_404(task_id)
    # Se il task è suggerito e l'utente non è il creatore, mostra 404
    if task.status == 'suggested' and (not current_user.is_authenticated or current_user.id != task.creator_id):
        abort(404)

    all_solutions = Solution.query.options(
        joinedload(Solution.submitter)
    ).filter_by(task_id=task_id).order_by(
        Solution.is_approved.desc(),
        Solution.ai_coherence_score.desc().nulls_last(),
        Solution.created_at.desc()
    ).all()

    user_solutions_count = 0
    if current_user.is_authenticated:
        user_solutions_count = Solution.query.filter_by(
            task_id=task_id,
            submitted_by_user_id=current_user.id
        ).count()

    can_submit_solution = user_solutions_count < MAX_SOLUTIONS_PER_USER

    return render_template('task_detail.html',
                           task=task,
                           project=task.project,
                           all_solutions=all_solutions,
                           can_submit_solution=can_submit_solution)


@tasks_bp.route('/task/<int:task_id>/activate_suggestion', methods=['POST'])
@login_required
def activate_suggestion(task_id: int) -> Response:
    form = BaseForm()
    if form.validate_on_submit():
        task = Task.query.get_or_404(task_id)
        project = Project.query.get_or_404(task.project_id)
        if project.creator_id != current_user.id:
            abort(403)
        
        if task.status == 'suggested':
            task.status = 'open'
            db.session.commit()
            flash('Suggerimento attivato con successo!', 'success')
        else:
            flash('Questo task non è un suggerimento o è già attivo.', 'warning')
        
        return redirect(url_for('projects.project_detail', project_id=task.project_id))
    else:
        flash('Si è verificato un errore di validazione. Riprova.', 'danger')
        task = db.session.get(Task, task_id)
        project_id_fallback = task.project_id if task else 1
        return redirect(url_for('projects.project_detail', project_id=project_id_fallback))


@tasks_bp.route('/task/<int:task_id>/submit_solution', methods=['GET', 'POST'])
@login_required
def submit_solution_form(task_id: int) -> Response | str:
    task: Task = Task.query.get_or_404(task_id)
    form = SolutionForm()

    if task.status not in ['open', 'in_progress']:
        flash(f"Questo task non è attualmente aperto a nuove soluzioni (stato: {task.status}).", "warning")
        return redirect(url_for('tasks.task_detail', task_id=task.id))
    
    user_solutions_count = Solution.query.filter_by(
        task_id=task_id, 
        submitted_by_user_id=current_user.id
    ).count()

    if user_solutions_count >= MAX_SOLUTIONS_PER_USER:
        flash(f"Hai già sottomesso il numero massimo di soluzioni ({MAX_SOLUTIONS_PER_USER}) per questo task.", "warning")
        return redirect(url_for('tasks.task_detail', task_id=task.id))

    if form.validate_on_submit():
        solution_content = form.solution_content.data
        file = form.solution_file.data
        
        # Gestione Pull Request URL (flusso software)
        pull_request_url = request.form.get('pull_request_url', '').strip()
        
        # Gestione file hardware multipli
        hardware_files = {
            'source_files': request.files.getlist('source_files'),
            'prototype_files': request.files.getlist('prototype_files'),
            'documentation_files': request.files.getlist('documentation_files'),
            'visual_files': request.files.getlist('visual_files')
        }
        
        # Setup upload folder
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'instance/uploads')
        if not os.path.isabs(upload_folder):
            upload_folder = os.path.join(current_app.instance_path, upload_folder)
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # Gestione file singolo (compatibilità)
        file_path = None
        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Tipo di file non supportato. Usa uno dei formati consentiti.', 'danger')
                return render_template('submit_solution.html', task=task, project=task.project, form=form)

            filename = secure_filename(f"{current_user.id}_{datetime.now(timezone.utc).timestamp()}_{file.filename}")
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            file_path = os.path.join(os.path.basename(upload_folder), filename)

        # Crea la soluzione con i nuovi campi
        new_solution = Solution(
            task_id=task.id,
            submitted_by_user_id=current_user.id,
            solution_content=solution_content,
            pull_request_url=pull_request_url if pull_request_url else None,
            file_path=file_path
        )
        
        try:
            analysis_results = analyze_solution_content(
                task.title, 
                task.description, 
                solution_content
            )
            if analysis_results and analysis_results.get('error') is None:
                new_solution.ai_coherence_score = analysis_results.get('coherence_score')
            else:
                flash("L'analisi AI non è riuscita a valutare la soluzione, ma è stata salvata comunque.", "info")
        except Exception as e:
            current_app.logger.error(f"Errore durante l'analisi AI della soluzione: {e}", exc_info=True)
            flash("Si è verificato un errore durante l'analisi AI. La soluzione è stata salvata senza valutazione.", "warning")

        db.session.add(new_solution)
        db.session.flush()  # Per ottenere l'ID della soluzione
        
        # Salva file hardware multipli
        solution_files = save_solution_files(hardware_files, new_solution.id, upload_folder)
        for solution_file in solution_files:
            db.session.add(solution_file)
        
        db.session.commit()
        
        # Messaggio di successo personalizzato
        if pull_request_url:
            flash("La tua soluzione GitHub è stata inviata con successo!", "success")
        elif solution_files:
            flash(f"La tua soluzione hardware è stata inviata con successo! ({len(solution_files)} file caricati)", "success")
        else:
            flash("La tua soluzione è stata inviata con successo!", "success")
            
        return redirect(url_for('tasks.task_detail', task_id=task.id))
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Errore nel campo '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('submit_solution.html', task=task, project=task.project, form=form)



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
from .services.github_service import GitHubService
from .utils import db_transaction

tasks_bp = Blueprint('tasks', __name__, template_folder='templates')
MAX_SOLUTIONS_PER_USER = 10
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'txt', 'pdf', 'zip', 'rar'}

# Estensioni specifiche per flusso hardware
HARDWARE_FILE_TYPES = {
    'source': {'step', 'stp', 'dwg', 'sch', 'brd', 'kicad_pcb', 'pro', 'lib'},
    'prototype': {'stl', '3mf', 'gcode', 'svg', 'dxf'},
    'documentation': {'pdf', 'docx', 'doc', 'md', 'txt', 'odt'},
    'visual': {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'mp4', 'webm', 'avi', 'mov'}
}

def get_github_service():
    """Helper per ottenere GitHubService con contesto Flask"""
    return GitHubService()

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
        
        with db_transaction():
            db.session.add(new_task)
            db.session.flush()
            
            # Notifica solo alle persone che possono vedere il task
            from .services.notification_service import NotificationService
            NotificationService.notify_task_created(new_task, project, current_user.id)
        
        # 🔄 SINCRONIZZAZIONE AUTOMATICA CON GITHUB (invisibile all'utente)
        try:
            get_github_service().sync_task_to_github(new_task, project)
            with db_transaction():
                pass  # Salva github_issue_number e github_synced_at
        except Exception as e:
            # Non bloccare la creazione del task se GitHub fallisce
            current_app.logger.warning(f"GitHub sync failed for task {new_task.id}: {e}")
        
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
        
        with db_transaction():
            db.session.add(new_task)
        
        # 🔄 SINCRONIZZAZIONE AUTOMATICA CON GITHUB (invisibile all'utente)
        try:
            get_github_service().sync_task_to_github(new_task, project)
            with db_transaction():
                pass  # Salva github_issue_number e github_synced_at
        except Exception as e:
            # Non bloccare la creazione del task se GitHub fallisce
            current_app.logger.warning(f"GitHub sync failed for AI task {new_task.id}: {e}")
        
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
        with db_transaction():
            task.results = results
            
            if task.status == 'open':
                task.status = 'in_progress'
            elif task.status == 'in_progress':
                task.status = 'submitted'
        
        # 🔄 SINCRONIZZAZIONE AUTOMATICA CON GITHUB (invisibile all'utente)
        try:
            project = Project.query.get(task.project_id)
            if project:
                get_github_service().sync_task_to_github(task, project)
                with db_transaction():
                    pass
        except Exception as e:
            current_app.logger.warning(f"GitHub sync failed for task {task.id}: {e}")
        
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
    with db_transaction():
        db.session.delete(task)

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
                           can_submit_solution=can_submit_solution,
                           user_solutions_count=user_solutions_count,
                           max_solutions=MAX_SOLUTIONS_PER_USER)


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
            with db_transaction():
                task.status = 'open'
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

    # Calcola contatore soluzioni utente
    user_solutions_count = Solution.query.filter_by(
        task_id=task_id, 
        submitted_by_user_id=current_user.id
    ).count()

    if task.status not in ['open', 'in_progress']:
        flash(f"Questo task non è attualmente aperto a nuove soluzioni (stato: {task.status}).", "warning")
        return redirect(url_for('tasks.task_detail', task_id=task.id))

    if user_solutions_count >= MAX_SOLUTIONS_PER_USER:
        flash(f"Hai già sottomesso il numero massimo di soluzioni ({MAX_SOLUTIONS_PER_USER}) per questo task.", "warning")
        return redirect(url_for('tasks.task_detail', task_id=task.id))
    
    # Template context comune
    template_context = {
        'task': task,
        'project': task.project,
        'form': form,
        'user_solutions_count': user_solutions_count,
        'max_solutions': MAX_SOLUTIONS_PER_USER
    }

    if form.validate_on_submit():
        solution_content = form.solution_content.data
        file = form.solution_file.data
        
        # 🔧 NUOVO: Gestione ZIP Upload (priorità massima)
        zip_file = form.solution_zip.data if hasattr(form, 'solution_zip') else None
        contribution_category = form.contribution_category.data if hasattr(form, 'contribution_category') else 'code'
        
        if zip_file and zip_file.filename:
            # ========== NUOVO FLUSSO: ZIP → Auto-PR ==========
            try:
                from app.services.zip_processor import ZipProcessor, ZipProcessorError
                from app.storage_helper import StorageHelper
                
                processor = ZipProcessor()
                storage = StorageHelper()
                
                # Estrai e valida ZIP
                try:
                    extracted_files = processor.extract_zip(zip_file)
                    current_app.logger.info(f"Extracted {len(extracted_files)} files from ZIP")
                except ZipProcessorError as e:
                    flash(f"❌ Errore ZIP: {str(e)}", "danger")
                    return render_template('submit_solution.html', **template_context)
                
                # Rileva tipo progetto
                project_type = processor.detect_project_type(extracted_files)
                current_app.logger.info(f"Detected project type: {project_type}")
                
                # Calcola statistiche (per ora senza base_repo_files)
                diff_stats = processor.calculate_diff_stats(extracted_files, base_files=None)
                
                # Crea Solution iniziale (senza PR ancora)
                new_solution = Solution(
                    task_id=task.id,
                    submitted_by_user_id=current_user.id,
                    solution_content=solution_content or f"Submission via ZIP upload ({len(extracted_files)} files)",
                    contribution_category=contribution_category,
                    files_modified=diff_stats['files_modified'],
                    files_added=diff_stats['files_added'],
                    lines_added=diff_stats['lines_added'],
                    lines_deleted=diff_stats['lines_deleted']
                )
                
                
                db.session.add(new_solution)
                db.session.flush()  # Ottieni solution.id
                
                # ⭐ NUOVO: AI Analysis del codice ZIP
                try:
                    code_summary = processor.extract_code_summary(extracted_files, max_chars=8000)
                    
                    if code_summary:
                        from app.ai_services import analyze_solution_content
                        
                        analysis_results = analyze_solution_content(
                            task.title,
                            task.description,
                            code_summary
                        )
                        
                        if analysis_results and analysis_results.get('error') is None:
                            new_solution.ai_coherence_score = analysis_results.get('coherence_score')
                            new_solution.ai_completeness_score = analysis_results.get('completeness_score')
                            current_app.logger.info(
                                f"AI analysis completed for ZIP solution #{new_solution.id}: "
                                f"coherence={new_solution.ai_coherence_score}, "
                                f"completeness={new_solution.ai_completeness_score}"
                            )
                except Exception as ai_error:
                    # Non bloccare se AI fallisce
                    current_app.logger.warning(f"AI analysis failed for ZIP solution: {ai_error}")
                
                # Salva file estratti nel database

                solution_files = []
                for file_info in extracted_files:
                    solution_file = SolutionFile(
                        solution_id=new_solution.id,
                        original_filename=os.path.basename(file_info['path']),
                        stored_filename=file_info['path'],
                        file_path=file_info['path'],
                        file_type='source',  # TODO: categorizzare meglio
                        content_type=contribution_category,
                        file_size=file_info['size'],
                        mime_type='text/plain' if file_info['type'] == 'text' else 'application/octet-stream'
                    )
                    solution_files.append(solution_file)
                    db.session.add(solution_file)
                
                # Crea PR su GitHub se repository configurato
                if task.project.github_repo_name:
                    github_service = get_github_service()
                    
                    if github_service and github_service.is_enabled():
                        user_info = {
                            'username': current_user.username,
                            'email': current_user.email,
                            'github_username': getattr(current_user, 'github_username', None)
                        }
                        
                        pr_result = github_service.create_pr_from_zip(
                            project=task.project,
                            solution=new_solution,
                            zip_files=extracted_files,
                            user_info=user_info
                        )
                        
                        if pr_result['success']:
                            # Aggiorna Solution con info GitHub
                            new_solution.pull_request_url = pr_result['pr_url']
                            new_solution.github_pr_number = pr_result['pr_number']
                            new_solution.github_branch = pr_result['branch']
                            new_solution.github_commit_sha = pr_result['commit_sha']
                            new_solution.github_pr_status = 'open'
                            
                            flash(f"✅ Soluzione caricata con successo! Pull Request #{pr_result['pr_number']} creata.", "success")
                        else:
                            current_app.logger.warning(f"GitHub PR creation failed: {pr_result.get('error')}")
                            flash(f"⚠️ Soluzione salvata ma PR GitHub fallita: {pr_result.get('error')}", "warning")
                    else:
                        current_app.logger.info("GitHub service not enabled - skipping PR creation")
                
                # Commit database
                with db_transaction():
                    pass
                
                # Cleanup
                processor.cleanup()
                
                return redirect(url_for('tasks.task_detail', task_id=task.id))
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error processing ZIP upload: {e}", exc_info=True)
                flash(f"❌ Errore imprevisto durante l'upload ZIP: {str(e)}", "danger")
                return render_template('submit_solution.html', task=task, project=task.project, form=form)
        
        # ========== FLUSSO ESISTENTE (fallback se no ZIP) ==========
        
        # Ottieni content_type dal form
        content_type = request.form.get('content_type', 'software')
        
        # Validazione content_type
        from app.models import CONTENT_TYPES
        if content_type not in CONTENT_TYPES:
            flash('Tipo di contenuto non valido', 'danger')
            return render_template('submit_solution.html', task=task, project=task.project, form=form)
        
        # ⭐ NUOVO: Ottieni modalità pubblicazione
        publish_method = request.form.get('publish_method', 'auto')  # 'auto' o 'manual'
        
        # ⭐ NUOVO: Gestione AUTO-PR (codice incollato)
        solution_code_auto = request.form.get('solution_code_auto', '').strip()
        
        pull_request_url = None
        auto_pr_created = False
        
        if publish_method == 'auto' and solution_code_auto and task.project.github_repo_name:
            # Modalità AUTO: Crea PR automatica dal codice incollato
            try:
                from services.github_auto_publisher import GitHubAutoPublisher, extract_code_from_textarea
                
                publisher = GitHubAutoPublisher()
                
                # Prepara content data
                content_data = extract_code_from_textarea(solution_code_auto, content_type)
                
                # Prepara task info
                task_info = {
                    'task_id': task.id,
                    'title': task.title,
                    'description': task.description or ''
                }
                
                # Prepara user info
                user_info = {
                    'username': current_user.username,
                    'email': current_user.email,
                    'github_username': getattr(current_user, 'github_username', None)
                }
                
                # Crea PR automatica (costruisci URL dal repo_name)
                repo_url = f"https://github.com/{task.project.github_repo_name}" if task.project.github_repo_name else None
                result = publisher.publish_solution_auto(
                    repo_url=repo_url,
                    content_data=content_data,
                    task_info=task_info,
                    user_info=user_info
                )
                
                if result['success']:
                    pull_request_url = result['pr_url']
                    auto_pr_created = True
                    flash(f"✨ Pull Request creata automaticamente! {pull_request_url}", "success")
                else:
                    flash(f"Errore nella creazione automatica PR: {result.get('error', 'Unknown error')}", "danger")
                    return render_template('submit_solution.html', **template_context)
                    
            except Exception as e:
                current_app.logger.error(f"Error in auto-PR creation: {e}", exc_info=True)
                flash(f"Errore imprevisto durante la creazione automatica della PR: {str(e)}", "danger")
                return render_template('submit_solution.html', task=task, project=task.project, form=form)
        
        elif publish_method == 'manual':
            # Modalità MANUAL: URL PR inserito manualmente
            pull_request_url = request.form.get('pull_request_url', '').strip()
            
            if not pull_request_url and content_type == 'software' and task.project.github_repo_name:
                flash('Per contributi software, inserisci l\'URL della Pull Request o usa la modalità automatica.', 'warning')
                return render_template('submit_solution.html', task=task, project=task.project, form=form)
        
        # Gestione file multipli per tutti i tipi
        uploaded_files = request.files.getlist('files')
        
        # Gestione file hardware legacy (compatibilità)
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

        # Crea la soluzione con content_type
        new_solution = Solution(
            task_id=task.id,
            submitted_by_user_id=current_user.id,
            solution_content=solution_content,
            pull_request_url=pull_request_url if pull_request_url else None,
            file_path=file_path,
            content_type=content_type  # NUOVO CAMPO
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

        # Salva file hardware multipli
        solution_files = save_solution_files(hardware_files, new_solution.id, upload_folder)
        
        with db_transaction():
            db.session.add(new_solution)
            db.session.flush()  # Per ottenere l'ID della soluzione
            for solution_file in solution_files:
                db.session.add(solution_file)
        
        # ========== NUOVO: GITHUB SYNC (NON BLOCCANTE) ==========
        # Sincronizza automaticamente con GitHub se abilitato GLOBALMENTE
        # Se fallisce, NON influenza il salvataggio locale (già fatto)
        try:
            from app.services import GitHubSyncService
            sync_service = GitHubSyncService()
            
            if sync_service.is_enabled():  # Check solo globale, non per progetto
                files_to_sync = []
                
                # Sincronizza file soluzione principale se presente
                if file_path and os.path.exists(os.path.join(current_app.instance_path, file_path)):
                    with open(os.path.join(current_app.instance_path, file_path), 'rb') as f:
                        files_to_sync.append({
                            'path': f"solutions/task_{task.id}/{os.path.basename(file_path)}",
                            'content': f.read(),
                            'message': f"Solution for task #{task.id} by {current_user.username}"
                        })
                
                # Sincronizza file multipli (hardware, documentation, etc.)
                for sol_file in solution_files:
                    full_path = os.path.join(upload_folder, sol_file.file_path)
                    if os.path.exists(full_path):
                        with open(full_path, 'rb') as f:
                            category = sol_file.file_category or 'misc'
                            files_to_sync.append({
                                'path': f"solutions/task_{task.id}/{category}/{os.path.basename(sol_file.file_path)}",
                                'content': f.read(),
                                'message': f"Solution file ({category}) for task #{task.id}"
                            })
                
                # Sincronizza content testuale (codice, documentazione)
                if solution_content and content_type in ['software', 'documentation']:
                    extension_map = {
                        'software': 'py',  # Default, potrebbe essere migliorato
                        'documentation': 'md'
                    }
                    ext = extension_map.get(content_type, 'txt')
                    files_to_sync.append({
                        'path': f"solutions/task_{task.id}/solution_{new_solution.id}.{ext}",
                        'content': solution_content.encode('utf-8'),
                        'message': f"Solution content for task #{task.id}"
                    })
                
                # Esegui sincronizzazione (se fallisce, solo log - non errore per utente)
                if files_to_sync:
                    results = sync_service.sync_multiple_files(task.project, files_to_sync)
                    if results['success'] > 0:
                        current_app.logger.info(
                            f"GitHub sync: {results['success']}/{len(files_to_sync)} files synced "
                            f"for solution {new_solution.id}"
                        )
                    if results['failed'] > 0:
                        current_app.logger.warning(
                            f"GitHub sync: {results['failed']} files failed to sync: {results['errors']}"
                        )
        except ImportError:
            # GitHub sync non disponibile - continua normalmente
            pass
        except Exception as e:
            # Errore GitHub sync - log ma NON fallire (soluzione già salvata)
            current_app.logger.warning(f"GitHub sync failed (non-critical) for solution {new_solution.id}: {e}")
        # ========== FINE GITHUB SYNC ==========
        
        # Messaggio di successo personalizzato per tipo
        content_type_labels = {
            'software': '💻 Software',
            'hardware': '🔧 Hardware',
            'design': '🎨 Design',
            'documentation': '📄 Documentazione',
            'media': '🎬 Media',
            'mixed': '🔀 Mista'
        }
        type_label = content_type_labels.get(content_type, 'Soluzione')
        
        if pull_request_url:
            flash(f"La tua soluzione {type_label} è stata inviata via GitHub con successo!", "success")
        elif solution_files:
            flash(f"La tua soluzione {type_label} è stata inviata con successo! ({len(solution_files)} file caricati)", "success")
        else:
            flash(f"La tua soluzione {type_label} è stata inviata con successo!", "success")
            
        return redirect(url_for('tasks.task_detail', task_id=task.id))
    elif request.method == 'POST':
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Errore nel campo '{getattr(form, field).label.text}': {error}", 'danger')

    return render_template('submit_solution.html', 
                           task=task, 
                           project=task.project, 
                           form=form,
                           user_solutions_count=user_solutions_count,
                           max_solutions=MAX_SOLUTIONS_PER_USER)




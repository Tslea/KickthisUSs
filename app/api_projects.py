# app/api_projects.py
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

from .extensions import db, limiter
from .models import Project, Task, Collaborator, Activity, Endorsement, ALLOWED_TASK_TYPES, SolutionFile
from .ai_services import AI_SERVICE_AVAILABLE, generate_project_details_from_pitch, generate_suggested_tasks
from .services.github_service import GitHubService
from .schemas import ProjectCreateSchema, validate_request_data

def get_github_service():
    """Helper per ottenere GitHubService con contesto Flask"""
    return GitHubService()

api_projects_bp = Blueprint('api_projects', __name__)

@api_projects_bp.route('/projects/generate-details', methods=['POST'])
@login_required
def generate_project_details_api():
    """
    Endpoint API per generare dettagli progetto con AI (pre-compilazione form).
    Usa la funzione esistente generate_project_details_from_pitch().
    """
    if not request.is_json:
        return jsonify({"error": "La richiesta deve essere in formato JSON."}), 415
    
    data = request.get_json()
    
    # Validazione con Pydantic
    is_valid, result = validate_request_data(ProjectCreateSchema, data)
    if not is_valid:
        return jsonify(result), 400
    
    pitch = result.pitch
    category = result.category
    project_type = result.project_type
    
    try:
        if not AI_SERVICE_AVAILABLE:
            return jsonify({"error": "Il servizio AI non è disponibile."}), 503
        
        # Usa funzione esistente
        details = generate_project_details_from_pitch(pitch.strip(), category, project_type)
        
        # Restituisce solo i dati generati (non crea progetto)
        return jsonify({
            "name": details.get('name', ''),
            "description": details.get('description', ''),
            "rewritten_pitch": details.get('rewritten_pitch', '')
        }), 200
        
    except ConnectionError as e:
        current_app.logger.error(f"Errore di connessione AI durante generazione dettagli: {e}", exc_info=True)
        return jsonify({"error": f"Errore di comunicazione con il servizio AI: {e}"}), 502
    except Exception as e:
        current_app.logger.error(f"Errore imprevisto durante generazione dettagli: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server durante la generazione dei dettagli."}), 500

@api_projects_bp.route('/projects', methods=['POST'])
@login_required
def create_project_api():
    """
    Endpoint API per creare un nuovo progetto.
    Riceve JSON, usa l'IA per arricchire i dati e salva tutto nel database.
    """
    if not request.is_json:
        return jsonify({"error": "La richiesta deve essere in formato JSON."}), 415

    data = request.get_json()
    
    # Validazione con Pydantic
    is_valid, result = validate_request_data(ProjectCreateSchema, data)
    if not is_valid:
        return jsonify(result), 400
    
    pitch = result.pitch
    category = result.category
    project_type = result.project_type
    cover_image_url = data.get('cover_image_url')
    private = data.get('private', False)
    
    # Sistema automatico: equity basata sul tipo di progetto
    if project_type == 'commercial':
        creator_equity = 10.0  # 10% automatico per progetti commerciali
    else:
        creator_equity = None  # Le ricerche scientifiche non hanno equity

    try:
        if AI_SERVICE_AVAILABLE:
            details = generate_project_details_from_pitch(pitch, category, project_type)
            project_name = details.get('name', 'Progetto Senza Nome')
            project_description = details.get('description', 'Nessuna descrizione generata.')
            rewritten_pitch = details.get('rewritten_pitch', pitch)
        else:
            project_name = "Nuovo Progetto (IA non disp.)"
            project_description = "Descrizione placeholder."
            rewritten_pitch = pitch
            suggested_tasks = []

        new_project = Project(
            creator_id=current_user.id,
            name=project_name,
            pitch=pitch,
            rewritten_pitch=rewritten_pitch,
            description=project_description,
            category=category,
            project_type=project_type,  # Nuovo campo
            creator_equity=creator_equity,  # Ora può essere None per ricerche scientifiche
            cover_image_url=cover_image_url,
            private=private  # Aggiungiamo il campo private
        )
        db.session.add(new_project)

        creator_as_collaborator = Collaborator(
            user_id=current_user.id,
            project=new_project,
            role='creator',
            equity_share=0
        )
        db.session.add(creator_as_collaborator)

        activity = Activity(
            user_id=current_user.id,
            action='create_project',
            project=new_project
        )
        db.session.add(activity)

        db.session.commit()

        # 🎯 INITIALIZE PHANTOM SHARES SYSTEM (NEW - for new projects)
        # New projects use shares system, old projects keep using equity (backward compatibility)
        try:
            from app.services.share_service import ShareService
            share_service = ShareService()
            share_service.initialize_project_shares(new_project)
            current_app.logger.info(f'Initialized phantom shares system for project {new_project.id} - User {current_user.id}')
        except Exception as e:
            current_app.logger.error(f'Failed to initialize shares system for project {new_project.id}: {str(e)}')
            # Fallback: use old equity system
            try:
                from app.services.equity_service import EquityService
                equity_service = EquityService()
                equity_service.initialize_creator_equity(new_project)
                current_app.logger.info(f'Fallback: Initialized creator equity (old system) for project {new_project.id}')
            except Exception as e2:
                current_app.logger.error(f'Failed to initialize equity system for project {new_project.id}: {str(e2)}')
                # Non bloccare la creazione del progetto, ma logga l'errore

        current_app.logger.info(f"Nuovo progetto creato con ID: {new_project.id} da utente {current_user.username}")

        return jsonify({
            "message": "Progetto creato con successo!",
            "project_id": new_project.id
        }), 201

    except ConnectionError as e:
        current_app.logger.error(f"Errore di connessione AI durante creazione progetto: {e}", exc_info=True)
        return jsonify({"error": f"Errore di comunicazione con il servizio AI: {e}"}), 502
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore imprevisto durante creazione progetto: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server durante la creazione del progetto."}), 500

@api_projects_bp.route('/projects/<int:project_id>/suggest-tasks', methods=['POST'])
@login_required
def suggest_tasks_api(project_id):
    """
    Endpoint API per generare task suggeriti dall'IA per un progetto esistente,
    evitando la creazione di duplicati e assegnando il corretto tipo di task.
    """
    project = Project.query.get_or_404(project_id)

    if project.creator_id != current_user.id:
        return jsonify({"error": "Solo il creatore del progetto può generare task."}), 403

    if not AI_SERVICE_AVAILABLE:
        return jsonify({"error": "Il servizio AI non è disponibile."}), 503

    try:
        # Recupera i task esistenti per questo progetto
        existing_tasks = []
        for task in project.tasks:
            existing_tasks.append({
                'title': task.title,
                'task_type': task.task_type,
                'equity_reward': task.equity_reward
            })

        # Genera i task basandosi sui dati del progetto
        suggested_tasks = generate_suggested_tasks(
            pitch=project.rewritten_pitch or project.pitch,
            category=project.category,
            description=project.description,
            existing_tasks=existing_tasks
        )

        if not suggested_tasks:
            return jsonify({"message": "L'IA non ha suggerito nuovi task.", "tasks": []}), 200

        # Filtra i task per evitare duplicati e li salva nel database
        newly_added_tasks = []
        existing_task_titles = {task.title.lower().strip() for task in project.tasks}
        
        for task_data in suggested_tasks:
            title = task_data.get('title')
            task_type = task_data.get('task_type')

            if not title or title.lower().strip() in existing_task_titles:
                continue 
            
            # Validazione: il tipo di task deve essere uno di quelli permessi
            if task_type not in ALLOWED_TASK_TYPES:
                task_type = 'proposal' # Default sicuro se l'IA fornisce un valore non valido

            task = Task(
                project_id=project.id,
                creator_id=current_user.id,
                title=title,
                description=task_data.get('description', 'Descrizione non definita'),
                task_type=task_type,
                equity_reward=task_data.get('equity_reward', 0.1),
                phase=task_data.get('phase', 'Planning'),
                difficulty=task_data.get('difficulty', 'Medium'),
                hypothesis=task_data.get('hypothesis') if task_type == 'validation' else None,
                test_method=task_data.get('test_method') if task_type == 'validation' else None,
                is_suggestion=True,  # Torniamo a True
                status='suggested'  # Torniamo a 'suggested'
            )
            db.session.add(task)
            db.session.flush() # Per ottenere l'ID del task prima del commit
            
            existing_task_titles.add(title.lower().strip())
            
            newly_added_tasks.append({
                'id': task.id,
                'title': task.title,
                'creator_id': task.creator_id,
                'description': task.description,
                'task_type': task.task_type,
                'equity_reward': task.equity_reward,
                'phase': task.phase,
                'difficulty': task.difficulty,
                'hypothesis': task.hypothesis,
                'test_method': task.test_method,
                'status': task.status,
                'task_type_display': ALLOWED_TASK_TYPES.get(task.task_type)
            })

        if not newly_added_tasks:
            return jsonify({
                "message": "L'IA non ha suggerito nuovi task validi o non duplicati.",
                "tasks": []
            }), 200

        activity = Activity(
            user_id=current_user.id,
            action='generate_ai_tasks',
            project_id=project.id
        )
        db.session.add(activity)
        db.session.commit()

        return jsonify({
            "message": f"{len(newly_added_tasks)} nuovi task suggeriti dall'IA sono stati aggiunti.",
            "tasks": newly_added_tasks
        }), 201

    except ConnectionError as e:
        current_app.logger.error(f"Errore di connessione AI durante suggerimento task: {e}", exc_info=True)
        return jsonify({"error": f"Errore di comunicazione con il servizio AI: {e}"}), 502
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore imprevisto durante suggerimento task: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server durante il suggerimento dei task."}), 500

@api_projects_bp.route('/projects/<int:project_id>/endorse', methods=['POST'])
@login_required
@limiter.limit("10 per minute;100 per hour")  # Limita endorsement/voti
def toggle_endorsement(project_id):
    """Aggiunge o rimuove il sostegno (endorsement) di un utente a un progetto."""
    try:
        project = Project.query.get_or_404(project_id)

        if project.creator_id == current_user.id:
            return jsonify({"error": "Non puoi sostenere il tuo stesso progetto."}), 403

        existing_endorsement = Endorsement.query.filter_by(
            user_id=current_user.id,
            project_id=project_id
        ).first()

        
        if existing_endorsement:
            db.session.delete(existing_endorsement)
            if project.endorsement_count > 0:
                project.endorsement_count -= 1
            action = 'removed'
        else:
            new_endorsement = Endorsement(user_id=current_user.id, project_id=project_id)
            db.session.add(new_endorsement)
            project.endorsement_count = (project.endorsement_count or 0) + 1
            action = 'added'

        db.session.commit()

        return jsonify({
            "success": True,
            "action": action,
            "new_endorsement_count": project.endorsement_count
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"API Errore Endorsement Progetto {project_id}: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server durante l'aggiornamento del sostegno."}), 500

@api_projects_bp.route('/projects/<int:project_id>/tasks', methods=['GET'])
@login_required
def get_project_tasks_api(project_id):
    """API per ottenere i task di un progetto"""
    try:
        # Verifica che l'utente abbia accesso al progetto
        project = Project.query.get_or_404(project_id)
        
        # Verifica permessi (creatore o collaboratore)
        if project.creator_id != current_user.id:
            collaborator = Collaborator.query.filter_by(
                project_id=project_id,
                user_id=current_user.id
            ).first()
            if not collaborator:
                return jsonify({"error": "Accesso negato"}), 403
        
        # Ottieni tutti i task del progetto
        tasks = Task.query.filter_by(project_id=project_id).all()
        
        tasks_data = []
        for task in tasks:
            # Ottieni gli obiettivi strategici collegati
            linked_objectives = [obj.id for obj in task.strategic_objectives]
            
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'task_type': task.task_type,
                'status': task.status,
                'phase': task.phase,
                'difficulty': task.difficulty,
                'equity_reward': task.equity_reward,
                'linked_objectives': linked_objectives,
                'position_x': getattr(task, 'position_x', None),
                'position_y': getattr(task, 'position_y', None),
                'created_at': task.created_at.isoformat() if task.created_at else None
            })
        
        return jsonify({
            'success': True,
            'tasks': tasks_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nel caricamento dei task: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server"}), 500

@api_projects_bp.route('/tasks/<int:task_id>/position', methods=['PUT'])
@login_required
def update_task_position_api(task_id):
    """API per aggiornare la posizione di un task nella mappa strategica"""
    try:
        task = Task.query.get_or_404(task_id)
        
        # Verifica che l'utente abbia accesso al progetto
        project = task.project
        if project.creator_id != current_user.id:
            collaborator = Collaborator.query.filter_by(
                project_id=project.id,
                user_id=current_user.id
            ).first()
            if not collaborator:
                return jsonify({"error": "Accesso negato"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dati non validi"}), 400
        
        # Aggiorna la posizione
        if 'position_x' in data:
            task.position_x = data['position_x']
        if 'position_y' in data:
            task.position_y = data['position_y']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'position_x': task.position_x,
            'position_y': task.position_y
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'aggiornamento posizione task: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server"}), 500

@api_projects_bp.route('/task/<int:task_id>/activate', methods=['POST'])
@login_required  
def activate_task_suggestion_api(task_id):
    """API endpoint per attivare un task suggerito"""
    try:
        task = Task.query.get_or_404(task_id)
        project = Project.query.get_or_404(task.project_id)
        
        # Verifica che l'utente sia il creatore del progetto o un collaboratore
        is_creator = project.creator_id == current_user.id
        is_collaborator = current_user in project.collaborators
        
        if not (is_creator or is_collaborator):
            return jsonify({"error": "Solo il creatore del progetto o i collaboratori possono attivare i task suggeriti."}), 403
        
        if task.status != 'suggested':
            return jsonify({"error": "Questo task non è un suggerimento o è già attivo."}), 400
        
        # Attiva il task
        task.status = 'open'
        task.is_suggestion = False
        db.session.commit()
        
        # Genera l'HTML per il task card (usando il template parziale)
        from flask import render_template
        task_html = render_template('partials/_task_card_tailwind.html', task=task, project=project, current_user=current_user)
        
        return jsonify({
            "success": True,
            "message": "Task attivato con successo!",
            "task": {
                "id": task.id,
                "title": task.title,
                "phase": task.phase,
                "status": task.status
            },
            "html": task_html
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore attivazione task suggerito: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server durante l'attivazione del task."}), 500

@api_projects_bp.route('/task/<int:task_id>/complete', methods=['POST'])
@login_required  
def complete_task_api(task_id):
    """API endpoint per completare un task"""
    try:
        task = Task.query.get_or_404(task_id)
        project = Project.query.get_or_404(task.project_id)
        
        # Verifica che l'utente sia il creatore del progetto o assegnato al task
        is_creator = project.creator_id == current_user.id
        is_assigned = task.assigned_to_id == current_user.id
        
        if not (is_creator or is_assigned):
            return jsonify({"error": "Solo il creatore del progetto o l'assegnato del task possono completarlo."}), 403
        
        if task.status != 'in_progress':
            return jsonify({"error": "Solo i task in corso possono essere completati."}), 400
        
        # Completa il task
        task.status = 'completed'
        db.session.commit()
        
        # 🔄 SINCRONIZZAZIONE AUTOMATICA CON GITHUB - chiude l'issue
        try:
            get_github_service().sync_task_to_github(task, project)
            db.session.commit()
        except Exception as e:
            current_app.logger.warning(f"GitHub sync failed for completed task {task.id}: {e}")
        
        return jsonify({
            "success": True,
            "message": "Task completato con successo!",
            "task": {
                "id": task.id,
                "title": task.title,
                "phase": task.phase,
                "status": task.status
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore completamento task: {e}", exc_info=True)
        return jsonify({"error": "Errore interno del server durante il completamento del task."}), 500

@api_projects_bp.route('/task/<int:task_id>/details', methods=['GET'])
@login_required
def get_task_details(task_id):
    """Get task details for editing"""
    try:
        task = Task.query.get_or_404(task_id)
        project = task.project
        
        # Verifica che l'utente sia il creatore del progetto o un collaboratore
        is_creator = current_user.id == project.creator_id
        is_collaborator = current_user in project.collaborators
        
        if not (is_creator or is_collaborator):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        return jsonify({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'task_type': task.task_type,
            'phase': task.phase,
            'difficulty': task.difficulty,
            'equity_reward': float(task.equity_reward),
            'hypothesis': task.hypothesis,
            'test_method': task.test_method,
            'is_private': task.is_private
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nel recupero dettagli task: {e}", exc_info=True)
        return jsonify({'error': 'Errore del server'}), 500

@api_projects_bp.route('/task/<int:task_id>/update-and-activate', methods=['POST'])
@login_required
def update_and_activate_task(task_id):
    """Update a suggested task and activate it"""
    try:
        task = Task.query.get_or_404(task_id)
        project = task.project
        
        # Verifica che l'utente sia il creatore del progetto o un collaboratore
        is_creator = current_user.id == project.creator_id
        is_collaborator = current_user in project.collaborators
        
        if not (is_creator or is_collaborator):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Verifica che il task sia ancora suggerito
        if task.status != 'suggested':
            return jsonify({'error': 'Il task non è più in stato suggerito'}), 400
        
        # Aggiorna i campi del task
        task.title = request.form.get('title', '').strip()
        task.description = request.form.get('description', '').strip()
        task.task_type = request.form.get('task_type', 'implementation')
        task.phase = request.form.get('phase', 'Development')
        task.difficulty = request.form.get('difficulty', 'Medium')
        task.equity_reward = float(request.form.get('equity_reward', 1.0))
        
        # Gestisci visibilità (privato/pubblico)
        is_private_value = request.form.get('is_private', 'false').lower()
        task.is_private = is_private_value in ['true', '1', 'yes']
        
        # Campi specifici per task di validazione
        if task.task_type == 'validation':
            task.hypothesis = request.form.get('hypothesis', '').strip()
            task.test_method = request.form.get('test_method', '').strip()
        else:
            task.hypothesis = None
            task.test_method = None
        
        # Attiva il task
        task.status = 'open'
        task.is_suggestion = False
        task.created_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Task aggiornato e attivato con successo'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nell'aggiornamento e attivazione del task: {e}", exc_info=True)
        return jsonify({'error': 'Errore del server'}), 500



from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, abort, Response, jsonify, send_file
from flask_login import login_required, current_user
from flask_wtf.csrf import validate_csrf, ValidationError
from sqlalchemy.orm import joinedload
from sqlalchemy import func, desc
from datetime import datetime, timezone
from werkzeug.routing import BuildError

from .extensions import db
from .models import (
    Project, Task, Endorsement, Collaborator, ProjectVote, Milestone,
    TransparencyReport,
    ALLOWED_PROJECT_CATEGORIES, ALLOWED_TASK_STATUS,
    ALLOWED_TASK_PHASES, ALLOWED_TASK_DIFFICULTIES, PROJECT_TYPES, ALLOWED_TASK_TYPES
)
from .forms import BaseForm, CreateProjectForm
from .utils import calculate_project_equity, clean_plain_text_field, clean_rich_text_field, db_transaction
from .email_middleware import email_verification_required
from .decorators import role_required
from .services.managed_repo_service import ManagedRepoService
from .workspace_utils import load_history_entries, list_session_metadata, synced_repo_dir
from .cache import cache

import requests
import shutil
import tempfile
import os
import zipfile

projects_bp = Blueprint('projects', __name__, template_folder='templates')

@projects_bp.route('/')
def home() -> Response | str:
    # Filtra i progetti privati
    recent_projects = Project.query.filter_by(private=False).order_by(Project.created_at.desc()).limit(8).all()
    
    # Se l'utente è autenticato, recupera i suoi voti (tutti i voti, non mensili)
    user_votes = {}
    if current_user.is_authenticated:
        votes = ProjectVote.query.filter(
            ProjectVote.user_id == current_user.id
        ).all()
        
        user_votes = {vote.project_id: True for vote in votes}
    
    # Calcola le metriche con caching (costose da calcolare)
    cached_metrics = cache.get('home_metrics')
    if cached_metrics is None:
        projects_count = Project.query.filter_by(private=False).count()
        collaborators_count = Collaborator.query.count()
        
        # Conta tutti i task di progetti pubblici (task pubblici o senza flag is_private)
        public_tasks_count = Task.query.join(Project).filter(
            Project.private == False,
            db.or_(Task.is_private == False, Task.is_private == None)
        ).count()
        
        # Cache metrics for 5 minutes
        cached_metrics = {
            'projects_count': projects_count,
            'collaborators_count': collaborators_count,
            'public_tasks_count': public_tasks_count
        }
        cache.set('home_metrics', cached_metrics, timeout=300)
    else:
        projects_count = cached_metrics['projects_count']
        collaborators_count = cached_metrics['collaborators_count']
        public_tasks_count = cached_metrics['public_tasks_count']
    
    return render_template('index.html', 
                         recent_projects=recent_projects,
                         user_votes=user_votes,
                         projects_count=projects_count,
                         collaborators_count=collaborators_count,
                         public_tasks_count=public_tasks_count)

@projects_bp.route('/projects')
def projects_list() -> Response | str:
    page: int = request.args.get('page', 1, type=int)
    per_page: int = 12
    category: str | None = request.args.get('category')
    project_type: str | None = request.args.get('project_type')  # Nuovo filtro
    
    # Creiamo una subquery usando un'espressione SQL diretta
    # Questa espressione restituisce i progetti pubblici e privati a cui l'utente ha accesso
    if current_user.is_authenticated:
        # Per gli utenti autenticati, mostra i progetti pubblici e quelli privati a cui hanno accesso
        # Costruiamo una condizione per i progetti che l'utente può vedere
        visible_projects_condition = db.or_(
            Project.private == False,  # Progetti pubblici
            db.and_(
                Project.private == True,
                db.or_(
                    Project.creator_id == current_user.id,
                    Project.id.in_(
                        db.session.query(Collaborator.project_id).filter(Collaborator.user_id == current_user.id)
                    )
                )
            )
        )
        query = Project.query.filter(visible_projects_condition)
    else:
        # Per gli utenti non autenticati, mostra solo i progetti pubblici
        query = Project.query.filter(Project.private == False)
    
    # Applica il filtro per categoria se presente
    if category:
        query = query.filter(Project.category == category)
    
    # --- NUOVO: Applica il filtro per tipo di progetto se presente ---
    if project_type:
        query = query.filter(Project.project_type == project_type)
        
    # Ordina i risultati
    query = query.order_by(Project.created_at.desc())
    
    # Pagina i risultati
    projects_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Se l'utente è autenticato, recupera i suoi voti (tutti i voti, non mensili)
    user_votes = {}
    if current_user.is_authenticated:
        votes = ProjectVote.query.filter(
            ProjectVote.user_id == current_user.id
        ).all()
        
        user_votes = {vote.project_id: True for vote in votes}
    
    return render_template('projects.html',
                           projects=projects_pagination.items,
                           pagination=projects_pagination,
                           categories=ALLOWED_PROJECT_CATEGORIES,
                           current_category=category,
                           current_project_type=project_type,  # Nuovo parametro
                           project_types=PROJECT_TYPES,       # Nuovo parametro
                           user_votes=user_votes)

@projects_bp.route('/create-project', methods=['GET', 'POST'])
@login_required
# NOTA: @email_verification_required rimosso per permettere creazione progetto senza verifica email
# Verifica email rimane richiesta per altre azioni (task, wiki, workspace) tramite middleware
def create_project_form() -> Response | str:
    """Mostra il form per creare un nuovo progetto."""
    form = CreateProjectForm()
    if request.method == 'POST':
        # Logica per gestire la creazione del progetto qui
        category = request.form.get('category')
        pitch = request.form.get('pitch', '')
        description = request.form.get('description', '')
        
        try:
            cleaned_pitch = clean_plain_text_field('project', 'pitch', pitch)
            cleaned_description = clean_rich_text_field('project', 'description', description)
        except ValueError as exc:
            flash(str(exc), 'error')
            return render_template(
                'create_project.html',
                allowed_categories=ALLOWED_PROJECT_CATEGORIES,
                project_types=PROJECT_TYPES,
                form=form
            )
        
        # --- NUOVO: SUPPORTO TIPO PROGETTO ---
        project_type = request.form.get('project_type', 'commercial')
        is_private = request.form.get('private') == 'y'
        cover_image_url = request.form.get('cover_image_url', '').strip() or None
        
        # Sistema automatico: 10% al creatore per progetti commerciali
        if project_type == 'commercial':
            creator_equity = 10.0  # 10% automatico, non più richiesto nel form
        else:
            creator_equity = None  # Ricerche scientifiche: nessuna equity
        
        # 🤖 GENERA NOME, REWRITTEN_PITCH E DESCRIZIONE CON AI
        project_name = None
        rewritten_pitch = None
        try:
            from app.ai_services import generate_project_details_from_pitch, AI_SERVICE_AVAILABLE
            if AI_SERVICE_AVAILABLE:
                details = generate_project_details_from_pitch(cleaned_pitch, category, project_type)
                project_name = details.get('name', 'Nuovo Progetto')
                rewritten_pitch = details.get('rewritten_pitch', cleaned_pitch)
                # Se la descrizione è vuota, usa quella generata dall'AI
                if not cleaned_description or cleaned_description.strip() == '':
                    cleaned_description = details.get('description', '')
        except Exception as e:
            current_app.logger.warning(f"Errore generazione dettagli AI: {e}")
            project_name = 'Nuovo Progetto'
            rewritten_pitch = cleaned_pitch  # Fallback al pitch originale
        
        # Pulizia del nome generato dall'AI
        try:
            cleaned_name = clean_plain_text_field('project', 'name', project_name)
        except ValueError:
            cleaned_name = project_name or 'Nuovo Progetto'
        
        new_project = Project(
            name=cleaned_name,
            category=category,
            pitch=cleaned_pitch,
            rewritten_pitch=rewritten_pitch,
            description=cleaned_description,
            project_type=project_type,  # Nuovo campo
            creator_equity=creator_equity,  # Ora può essere None per ricerche scientifiche
            creator_id=current_user.id,
            platform_fee=1.0,
            private=is_private,
            cover_image_url=cover_image_url
        )
        with db_transaction():
            db.session.add(new_project)
        
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
        
        # 🤖 GENERAZIONE AUTOMATICA GUIDE AI
        try:
            from app.ai_services import analyze_with_ai
            from datetime import datetime, timezone
            
            # Prepara informazioni del progetto per AI
            project_info = f"""
            NOME PROGETTO: {name}
            CATEGORIA: {category}
            PITCH: {pitch or 'Non specificato'}
            DESCRIZIONE: {description or 'Non specificata'}
            """
            
            # Genera guida MVP
            mvp_prompt = f"""
            TASK: Crea una guida dettagliata step-by-step per sviluppare un MVP (Minimum Viable Product) per il seguente progetto.
            
            INFORMAZIONI PROGETTO:
            {project_info}
            
            ISTRUZIONI:
            1. Analizza il progetto e identifica le funzionalità core essenziali per un MVP
            2. Crea una roadmap step-by-step chiara e actionable
            3. Ogni step deve essere specifico e realizzabile
            4. Includi considerazioni tecniche, di design e di business
            5. Organizza in fasi logiche e progressive
            6. Stima tempi realistici per ogni fase
            
            FORMATO RISPOSTA:
            # 📋 Guida MVP: {name}
            
            ## 🎯 Obiettivo MVP
            [Descrizione chiara di cosa deve fare l'MVP]
            
            ## ⚡ Funzionalità Core (Must-Have)
            1. [Funzionalità essenziale 1]
            2. [Funzionalità essenziale 2]
            
            ## 🚀 Roadmap di Sviluppo
            
            ### Fase 1: Fondamenta (Settimana 1-2)
            - [ ] [Task specifico]
            - [ ] [Task specifico]
            
            ### Fase 2: Funzionalità Core (Settimana 3-4)
            - [ ] [Task specifico]
            - [ ] [Task specifico]
            
            ### Fase 3: Testing e Rilascio (Settimana 5-6)
            - [ ] [Task specifico]
            - [ ] [Task specifico]
            
            ## 🛠️ Stack Tecnologico Consigliato
            - **Frontend**: [Raccomandazione]
            - **Backend**: [Raccomandazione]
            - **Database**: [Raccomandazione]
            - **Hosting**: [Raccomandazione]
            
            ## 📊 Metriche di Successo
            1. [Metrica misurabile]
            2. [Metrica misurabile]
            """
            
            # Genera analisi fattibilità
            feasibility_prompt = f"""
            TASK: Effettua un'analisi realistica e professionale delle possibilità di successo del seguente progetto.
            
            INFORMAZIONI PROGETTO:
            {project_info}
            
            ISTRUZIONI:
            1. Analizza il progetto da prospettive multiple: tecnica, di mercato, finanziaria
            2. Identifica opportunità e sfide realistiche
            3. Fornisci valutazioni honest e costruttive
            4. Includi considerazioni su competitors e market fit
            5. Suggerisci miglioramenti e alternative
            6. Usa un tono professionale ma accessibile
            
            FORMATO RISPOSTA:
            # 📊 Analisi di Fattibilità: {name}
            
            ## ✅ Punti di Forza
            1. [Punto forte identificato]
            2. [Punto forte identificato]
            
            ## ⚠️ Sfide e Rischi
            1. [Sfida realistica]
            2. [Sfida realistica]
            
            ## 🎯 Market Analysis
            - **Dimensione del mercato**: [Valutazione]
            - **Competitors principali**: [Analisi competitors]
            - **Differenziazione**: [Come distinguersi]
            
            ## 💰 Considerazioni Finanziarie
            - **Costi di sviluppo stimati**: [Stima realistica]
            - **Possibili modelli di monetizzazione**: [Opzioni]
            - **Tempo per break-even**: [Stima]
            
            ## 🚀 Probabilità di Successo
            - **Tecnica**: [Valutazione 1-10 con spiegazione]
            - **Di mercato**: [Valutazione 1-10 con spiegazione]
            - **Complessiva**: [Valutazione finale]
            
            ## 💡 Raccomandazioni
            1. [Raccomandazione specifica]
            2. [Raccomandazione specifica]
            
            ## 🎯 Next Steps Prioritari
            1. [Azione concreta da intraprendere]
            2. [Azione concreta da intraprendere]
            """
            
            # Genera le guide AI
            mvp_guide = analyze_with_ai(mvp_prompt, max_tokens=1500)
            feasibility_analysis = analyze_with_ai(feasibility_prompt, max_tokens=1500)
            
            # Salva nel database
            if mvp_guide and feasibility_analysis:
                with db_transaction():
                    new_project.ai_mvp_guide = mvp_guide
                    new_project.ai_feasibility_analysis = feasibility_analysis
                    new_project.ai_guide_generated_at = datetime.now(timezone.utc)
                flash('Progetto creato con successo! Le guide AI sono state generate automaticamente.', 'success')
            else:
                flash('Progetto creato con successo! Le guide AI saranno disponibili a breve.', 'info')
                
        except Exception as e:
            # Non bloccare la creazione del progetto se la generazione AI fallisce
            current_app.logger.error(f"Errore generazione guide AI: {str(e)}")
            flash('Progetto creato con successo!', 'success')
        
        # ========== REPOSITORY GESTITO ==========
        try:
            repo_service = ManagedRepoService()
            repo_record = repo_service.initialize_managed_repository(new_project)
            if repo_record and repo_record.provider == 'github_managed':
                current_app.logger.info("Managed GitHub repo ready for project %s (%s)", new_project.id, repo_record.repo_name)
        except Exception as e:
            current_app.logger.warning(f"Managed repo setup failed for project {new_project.id}: {e}")
        # ========== FINE SETUP ==========
        
        return redirect(url_for('projects.project_detail', project_id=new_project.id))
    return render_template('create_project.html',
                           allowed_categories=ALLOWED_PROJECT_CATEGORIES,
                           project_types=PROJECT_TYPES,
                           form=form)

@projects_bp.route('/project/<int:project_id>/ai-guide')
def project_ai_guide(project_id: int) -> Response | str:
    """Visualizza le guide AI del progetto"""
    project = Project.query.get_or_404(project_id)
    
    # Verifica accesso al progetto
    if project.private:
        if not current_user.is_authenticated:
            flash("Questo è un progetto privato. Devi effettuare il login per accedervi.", "warning")
            return redirect(url_for('auth.login'))
            
        # Controlla se l'utente è autorizzato ad accedere
        is_creator = project.creator_id == current_user.id
        is_collaborator = Collaborator.query.filter_by(
            project_id=project.id, user_id=current_user.id
        ).first() is not None
        
        if not (is_creator or is_collaborator):
            flash("Non sei autorizzato ad accedere a questo progetto privato.", "error")
            return redirect(url_for('projects.projects_list'))
    
    return render_template('ai_project_guide.html', project=project)

@projects_bp.route('/project/<int:project_id>')
def project_detail(project_id: int) -> Response | str:
    project: Project = Project.query.options(joinedload(Project.creator)).get_or_404(project_id)
    collaborator_record = None
    if current_user.is_authenticated:
        collaborator_record = Collaborator.query.filter_by(
            project_id=project.id, user_id=current_user.id
        ).first()
    is_creator = current_user.is_authenticated and current_user.id == project.creator_id
    is_collaborator = collaborator_record is not None if current_user.is_authenticated else False
    
    # Verifica accesso ai progetti privati
    if project.private:
        if not current_user.is_authenticated:
            flash("Questo è un progetto privato. Devi effettuare il login per accedervi.", "warning")
            return redirect(url_for('auth.login'))
        
        if not (is_creator or is_collaborator):
            flash("Non sei autorizzato ad accedere a questo progetto privato.", "error")
            return redirect(url_for('projects.projects_list'))
    
    # Correzione: Passa l'intero oggetto 'project'
    distributed_equity = calculate_project_equity(project)
    
    creator_equity = project.creator_equity
    distributed_equity = sum([c.equity_share for c in project.collaborators])
    platform_fee = getattr(project, 'platform_fee', 1.0)
    remaining_equity = 100 - creator_equity - distributed_equity - platform_fee
    
    # Auto-initialize shares system for commercial projects if missing
    if project.is_commercial and not project.uses_shares_system():
        try:
            from .services.share_service import ShareService
            share_service = ShareService()
            share_service.initialize_project_shares(project)
            db.session.commit()
            current_app.logger.info(f'Auto-initialized shares system for project {project.id} via project detail page')
        except Exception as e:
            current_app.logger.error(f'Failed to auto-initialize shares system for project {project.id}: {str(e)}')
            db.session.rollback()
    
    # Get transparency data for public section
    transparency_data = None
    try:
        from .services.reporting_service import ReportingService
        reporting_service = ReportingService()
        transparency_data = reporting_service.get_transparency_data(project, anonymize_holders=False)
    except Exception as e:
        current_app.logger.error(f"Error loading transparency data: {e}", exc_info=True)
        # Fallback: create minimal transparency data
        try:
            uses_shares = project.uses_shares_system() if hasattr(project, 'uses_shares_system') else False
        except:
            uses_shares = False
        transparency_data = {
            'uses_shares_system': uses_shares,
            'shares': {'total': 0, 'distributed': 0, 'available': 0, 'holders_count': 0, 'holders': []},
            'revenue': {'total': 0, 'currency': 'EUR', 'records_count': 0, 'history': []},
            'distributions': {'total': 0, 'count': 0, 'history': []},
            'growth': {'new_holders_this_month': 0}
        }

    form = BaseForm()

    user_has_endorsed = False
    user_has_voted_this_month = False
    if current_user.is_authenticated:
        user_has_endorsed = Endorsement.query.filter_by(user_id=current_user.id, project_id=project.id).first() is not None
        
        # Controlla se l'utente ha già votato questo progetto questo mese
        current_date = datetime.now()
        current_month = int(f"{current_date.year}{current_date.month:02d}")
        current_year = current_date.year
        
        user_has_voted_this_month = ProjectVote.query.filter(
            ProjectVote.user_id == current_user.id,
            ProjectVote.project_id == project.id,
            ProjectVote.vote_month == current_month,
            ProjectVote.vote_year == current_year
        ).first() is not None

    tasks_by_phase = {phase_key: [] for phase_key in ALLOWED_TASK_PHASES.keys()}
    
    # Filtra i task in base ai permessi di visualizzazione
    all_active_tasks = project.tasks.filter(Task.status.in_(['open', 'in_progress', 'submitted', 'suggested'])).all()
    active_tasks = [task for task in all_active_tasks if task.can_view(current_user)]
    
    for task in active_tasks:
        if task.phase in tasks_by_phase:
            tasks_by_phase[task.phase].append(task)

    all_completed_tasks = project.tasks.filter(Task.status.in_(['approved', 'closed'])).order_by(Task.id.desc()).all()
    completed_tasks = [task for task in all_completed_tasks if task.can_view(current_user)]
    
    # Mappatura vecchi tipi -> nuovi tipi per retrocompatibilità
    legacy_type_mapping = {
        'proposal': 'strategy',      # Vecchie proposte -> Strategy
        'implementation': 'code'     # Vecchie implementazioni -> Code
    }
    
    # Raggruppa task attivi per tipologia (task_type)
    tasks_by_type = {type_key: [] for type_key in ALLOWED_TASK_TYPES.keys()}
    for task in active_tasks:
        task_type = task.task_type or 'code'  # default se non specificato
        # Mappa vecchi tipi ai nuovi
        task_type = legacy_type_mapping.get(task_type, task_type)
        if task_type in tasks_by_type:
            tasks_by_type[task_type].append(task)
        else:
            tasks_by_type['code'].append(task)
    
    # Raggruppa task completati per tipologia e ordinati cronologicamente
    completed_tasks_by_type = {type_key: [] for type_key in ALLOWED_TASK_TYPES.keys()}
    for task in completed_tasks:
        task_type = task.task_type or 'code'
        # Mappa vecchi tipi ai nuovi
        task_type = legacy_type_mapping.get(task_type, task_type)
        if task_type in completed_tasks_by_type:
            completed_tasks_by_type[task_type].append(task)
        else:
            completed_tasks_by_type['code'].append(task)
    
    # Determine tasks to show based on status filter
    status_filter = request.args.get('status')
    current_status = status_filter if status_filter in ['completed', 'in_progress', 'open'] else 'active'
    if status_filter == 'completed':
        tasks = completed_tasks
    elif status_filter == 'in_progress':
        tasks = [t for t in active_tasks if t.status == 'in_progress']
    elif status_filter == 'open':
        tasks = [t for t in active_tasks if t.status == 'open']
    else:
        tasks = active_tasks

    has_active_tasks = bool(active_tasks)

    collaborators = Collaborator.query.options(joinedload(Collaborator.user)).filter_by(project_id=project.id).order_by(Collaborator.equity_share.desc()).all()

    # Ottieni le milestone del progetto
    milestones = Milestone.query.filter_by(project_id=project.id).order_by(
        Milestone.display_order,
        Milestone.created_at
    ).all()
    
    # Verifica se l'utente può modificare le milestone
    can_edit_milestones = False
    if current_user.is_authenticated:
        can_edit_milestones = is_creator or is_collaborator

    workspace_repo_info = None
    if project.repository:
        workspace_repo_info = {
            'provider': project.repository.provider,
            'repo_name': project.repository.repo_name,
            'branch': project.repository.branch,
            'status': project.repository.status,
            'last_sync_at': project.repository.last_sync_at
        }
    
    workspace_history = load_history_entries(project.id, limit=5)
    for history_item in workspace_history:
        files = history_item.get('files') or []
        if not history_item.get('file_count'):
            history_item['file_count'] = len(files)
    workspace_sessions = []
    for session_meta in list_session_metadata(project.id, limit=5):
        workspace_sessions.append({
            'session_id': session_meta.get('session_id'),
            'status': session_meta.get('status', 'pending'),
            'type': session_meta.get('type', 'manual'),
            'file_count': session_meta.get('file_count') or len(session_meta.get('files') or []),
            'total_size': session_meta.get('total_size'),
            'created_at': session_meta.get('created_at'),
            'updated_at': session_meta.get('updated_at'),
            'finalized_at': session_meta.get('finalized_at')
        })
    
    can_manage_workspace = is_creator or is_collaborator
    
    workspace_api_urls = None
    try:
        download_base = url_for('api_uploads.download_project_file', project_id=project.id, requested_path='')
        workspace_api_urls = {
            'zip': url_for('api_uploads.upload_project_zip', project_id=project.id),
            'file': url_for('api_uploads.upload_project_file', project_id=project.id),
            'finalize': url_for('api_uploads.finalize_upload_session', project_id=project.id),
            'cancel_template': url_for('api_uploads.delete_upload_session', project_id=project.id, session_id='__SESSION__'),
            'status': url_for('api_uploads.get_sync_status', project_id=project.id),
            'tree': url_for('api_uploads.list_project_files', project_id=project.id),
            'sign': url_for('api_uploads.sign_project_file', project_id=project.id),
            'download_base': download_base.rstrip('/')
        }
        print(f"[WORKSPACE URLs] Workspace API URLs configured for project {project.id}:")
        print(f"  - ZIP URL: {workspace_api_urls['zip']}")
        print(f"  - Status URL: {workspace_api_urls['status']}")
    except BuildError as exc:
        print(f"[WORKSPACE URLs] Workspace API routes unavailable: {exc}")
        current_app.logger.warning("Workspace API routes unavailable: %s", exc)
        workspace_api_urls = None
    
    workspace_api_available = workspace_api_urls is not None
    workspace_limits = {
        'zip_mb': current_app.config.get('PROJECT_WORKSPACE_MAX_ZIP_MB', 500),
        'file_mb': current_app.config.get('PROJECT_WORKSPACE_MAX_FILE_MB', 100)
    }
    
    return render_template('project_detail.html',
                           project=project,
                           tasks_by_phase=tasks_by_phase,
                           tasks_by_type=tasks_by_type,
                           completed_tasks=completed_tasks,
                           completed_tasks_by_type=completed_tasks_by_type,
                           has_active_tasks=has_active_tasks,
                           collaborators=collaborators,
                           user_has_endorsed=user_has_endorsed,
                           user_has_voted_this_month=user_has_voted_this_month,
                           ALLOWED_TASK_STATUS=ALLOWED_TASK_STATUS,
                           ALLOWED_TASK_PHASES=ALLOWED_TASK_PHASES,
                           ALLOWED_TASK_TYPES=ALLOWED_TASK_TYPES,
                           transparency_data=transparency_data,
                           creator_equity=creator_equity,
                           distributed_equity=distributed_equity,
                           platform_fee=platform_fee,
                           remaining_equity=remaining_equity,
                           ALLOWED_TASK_DIFFICULTIES=ALLOWED_TASK_DIFFICULTIES,
                           milestones=milestones,
                           can_edit_milestones=can_edit_milestones,
                           can_manage_workspace=can_manage_workspace,
                           workspace_repo=workspace_repo_info,
                           workspace_history=workspace_history,
                           workspace_sessions=workspace_sessions,
                           workspace_api_urls=workspace_api_urls,
                           workspace_api_available=workspace_api_available,
                           workspace_limits=workspace_limits,
                           tasks=tasks,
                           current_status=current_status,
                           form=form)


@projects_bp.route('/project/<int:project_id>/workspace')
@login_required
def project_workspace(project_id: int) -> Response | str:
    """
    Full-featured workspace page for file management, uploads, and GitHub sync.
    """
    project = Project.query.get_or_404(project_id)
    is_creator = project.creator_id == current_user.id
    collaborator = Collaborator.query.filter_by(
        project_id=project.id,
        user_id=current_user.id
    ).first()
    
    if not (is_creator or collaborator):
        flash("Non hai i permessi per accedere al workspace di questo progetto.", "error")
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    # Load workspace data
    workspace_repo_info = None
    if project.repository:
        workspace_repo_info = {
            'provider': project.repository.provider,
            'repo_name': project.repository.repo_name,
            'branch': project.repository.branch,
            'status': project.repository.status,
            'last_sync_at': project.repository.last_sync_at
        }
    
    workspace_history = load_history_entries(project.id, limit=10)
    for history_item in workspace_history:
        files = history_item.get('files') or []
        if not history_item.get('file_count'):
            history_item['file_count'] = len(files)
    
    # Get API URLs for uploads
    workspace_api_urls = None
    try:
        workspace_api_urls = {
            'zip': url_for('api_uploads.upload_project_zip', project_id=project.id),
            'file': url_for('api_uploads.upload_project_file', project_id=project.id),
            'finalize': url_for('api_uploads.finalize_upload_session', project_id=project.id),
            'status': url_for('api_uploads.get_sync_status', project_id=project.id),
            'tree': url_for('api_uploads.list_project_files', project_id=project.id),
        }
    except BuildError:
        current_app.logger.warning("Workspace API routes unavailable")
        workspace_api_urls = None
    
    workspace_limits = {
        'zip_mb': current_app.config.get('PROJECT_WORKSPACE_MAX_ZIP_MB', 500),
        'file_mb': current_app.config.get('PROJECT_WORKSPACE_MAX_FILE_MB', 100)
    }
    
    return render_template('project_workspace.html',
                           project=project,
                           workspace_repo=workspace_repo_info,
                           workspace_history=workspace_history,
                           workspace_api_urls=workspace_api_urls,
                           workspace_limits=workspace_limits)


@projects_bp.route('/project/<int:project_id>/equity')
@login_required
def project_equity(project_id: int) -> Response | str:
    """
    Display project cap table (equity distribution).
    Only visible to project creator and collaborators.
    """
    from .services.equity_service import EquityService
    
    project = Project.query.options(
        joinedload(Project.creator)
    ).get_or_404(project_id)
    
    # Check permissions: only creator and collaborators can view
    is_creator = current_user.id == project.creator_id
    is_collaborator = Collaborator.query.filter_by(
        project_id=project.id,
        user_id=current_user.id
    ).first() is not None
    
    if not (is_creator or is_collaborator):
        flash('⛔ Solo il creatore e i collaboratori possono vedere la distribuzione equity.', 'error')
        abort(403)
    
    # Get cap table
    equity_service = EquityService()
    cap_table = equity_service.get_cap_table(project)
    
    # Get equity stats
    total_distributed = project.get_total_equity_distributed()
    available_equity = project.get_available_equity()
    
    # Validate equity distribution
    validation_result = equity_service.validate_and_fix_equity(project)
    
    # Get equity configuration (query separately to avoid relationship issues)
    from .models import EquityConfiguration
    equity_config = EquityConfiguration.query.filter_by(project_id=project.id).first()
    
    return render_template('project_equity.html',
                         project=project,
                         cap_table=cap_table,
                         total_distributed=total_distributed,
                         available_equity=available_equity,
                         validation_result=validation_result,
                         equity_config=equity_config,
                         is_creator=is_creator)


@projects_bp.route('/project/<int:project_id>/equity/history')
@login_required
def project_equity_history(project_id: int) -> Response | str:
    """
    Display project equity history (audit log).
    Only visible to project creator and collaborators.
    """
    from .models import EquityHistory
    
    project = Project.query.options(
        joinedload(Project.creator)
    ).get_or_404(project_id)
    
    # Check permissions: only creator and collaborators can view
    is_creator = current_user.id == project.creator_id
    is_collaborator = Collaborator.query.filter_by(
        project_id=project.id,
        user_id=current_user.id
    ).first() is not None
    
    if not (is_creator or is_collaborator):
        flash('⛔ Solo il creatore e i collaboratori possono vedere lo storico equity.', 'error')
        abort(403)
    
    # Get equity history with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    history_query = EquityHistory.query.filter_by(
        project_id=project.id
    ).options(
        joinedload(EquityHistory.user),
        joinedload(EquityHistory.changed_by)
    ).order_by(EquityHistory.created_at.desc())
    
    history_pagination = history_query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Get summary stats
    total_grants = EquityHistory.query.filter_by(
        project_id=project.id,
        action='grant'
    ).count()
    
    total_equity_granted = db.session.query(
        db.func.sum(EquityHistory.equity_change)
    ).filter(
        EquityHistory.project_id == project.id,
        EquityHistory.action == 'grant'
    ).scalar() or 0.0
    
    return render_template('project_equity_history.html',
                         project=project,
                         history_pagination=history_pagination,
                         total_grants=total_grants,
                         total_equity_granted=total_equity_granted,
                         is_creator=is_creator)


# ============================================
# TRANSPARENCY SYSTEM (PUBLIC)
# ============================================

@projects_bp.route('/project/<int:project_id>/transparency')
def project_transparency(project_id: int) -> Response | str:
    """
    PUBLIC transparency dashboard for a project.
    Accessible to everyone, no login required.
    """
    from .services.reporting_service import ReportingService
    from .services.share_service import ShareService
    
    project = Project.query.get_or_404(project_id)
    
    # Auto-initialize shares system for commercial projects if missing
    if project.is_commercial and not project.uses_shares_system():
        try:
            share_service = ShareService()
            share_service.initialize_project_shares(project)
            db.session.commit()
            current_app.logger.info(f'Auto-initialized shares system for project {project.id} via transparency page')
        except Exception as e:
            current_app.logger.error(f'Failed to auto-initialize shares system for project {project.id}: {str(e)}')
            db.session.rollback()
    
    # Get anonymization preference (default: False for public transparency)
    anonymize = request.args.get('anonymize', 'false').lower() == 'true'
    
    # Get transparency data
    reporting_service = ReportingService()
    transparency_data = reporting_service.get_transparency_data(
        project, 
        include_private_info=False,
        anonymize_holders=anonymize
    )
    
    # Get monthly reports
    monthly_reports = project.transparency_reports.order_by(
        desc(TransparencyReport.report_year),
        desc(TransparencyReport.report_month)
    ).limit(12).all()
    
    # Check if user is creator/collaborator (for additional actions)
    is_creator = False
    is_collaborator = False
    if current_user.is_authenticated:
        is_creator = project.creator_id == current_user.id
        is_collaborator = Collaborator.query.filter_by(
            project_id=project.id,
            user_id=current_user.id
        ).first() is not None
    
    return render_template('projects/transparency.html',
                         project=project,
                         transparency_data=transparency_data,
                         monthly_reports=monthly_reports,
                         anonymize=anonymize,
                         is_creator=is_creator,
                         is_collaborator=is_collaborator)


@projects_bp.route('/api/projects/<int:project_id>/transparency')
def api_project_transparency(project_id: int):
    """
    Public API endpoint for transparency data.
    Returns JSON with all transparency information.
    """
    from .services.reporting_service import ReportingService
    from flask import jsonify
    
    project = Project.query.get_or_404(project_id)
    
    # Get anonymization preference
    anonymize = request.args.get('anonymize', 'false').lower() == 'true'
    
    # Get transparency data
    reporting_service = ReportingService()
    transparency_data = reporting_service.get_transparency_data(
        project,
        include_private_info=False,
        anonymize_holders=anonymize
    )
    
    return jsonify(transparency_data)


@projects_bp.route('/project/<int:project_id>/transparency/export')
def export_transparency(project_id: int):
    """
    Export transparency data as CSV or JSON.
    """
    from .services.reporting_service import ReportingService
    from flask import Response
    
    project = Project.query.get_or_404(project_id)
    
    # Get format (default: json)
    export_format = request.args.get('format', 'json').lower()
    anonymize = request.args.get('anonymize', 'false').lower() == 'true'
    
    if export_format not in ['json', 'csv']:
        flash('Invalid format. Use "json" or "csv".', 'error')
        return redirect(url_for('projects.project_transparency', project_id=project_id))
    
    # Generate export
    reporting_service = ReportingService()
    export_data = reporting_service.export_transparency_data(
        project,
        format=export_format,
        anonymize_holders=anonymize
    )
    
    # Create response
    if export_format == 'json':
        response = Response(
            export_data,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=transparency_{project.id}_{datetime.now(timezone.utc).strftime("%Y%m%d")}.json'
            }
        )
    else:  # csv
        response = Response(
            export_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=transparency_{project.id}_{datetime.now(timezone.utc).strftime("%Y%m%d")}.csv'
            }
        )
    
    return response


@projects_bp.route('/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id: int):
    """Elimina un progetto. Solo il creatore può eliminarlo."""
    project = Project.query.get_or_404(project_id)
    
    # Solo il creatore può eliminare il progetto
    if project.creator_id != current_user.id:
        flash("Solo il creatore può eliminare il progetto.", "error")
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    # Verifica conferma
    confirmation = request.form.get('confirmation', '').strip()
    project_name = request.form.get('project_name', '').strip()
    
    if confirmation != 'ELIMINA' or project_name != project.name:
        flash("Conferma non valida. Devi scrivere 'ELIMINA' e il nome esatto del progetto.", "error")
        return redirect(url_for('projects.edit_project_form', project_id=project_id))
    
    try:
        from .models import ShareHistory, EquityHistory, PhantomShare, ProjectEquity
        
        project_name_for_flash = project.name
        with db_transaction():
            # Elimina manualmente i record correlati per sicurezza (in caso il cascade non funzioni)
            ShareHistory.query.filter_by(project_id=project_id).delete()
            EquityHistory.query.filter_by(project_id=project_id).delete()
            PhantomShare.query.filter_by(project_id=project_id).delete()
            ProjectEquity.query.filter_by(project_id=project_id).delete()
            
            # Le relazioni cascade elimineranno automaticamente:
            # - tasks, collaborators, activities, endorsements, repository
            db.session.delete(project)
        
        flash(f"Il progetto '{project_name_for_flash}' è stato eliminato definitivamente.", "success")
        current_app.logger.info(f"Progetto {project_id} eliminato da utente {current_user.id}")
        return redirect(url_for('projects.home'))
    except Exception as exc:
        current_app.logger.error(f"Errore eliminazione progetto {project_id}: {exc}", exc_info=True)
        flash("Si è verificato un errore durante l'eliminazione del progetto.", "error")
        return redirect(url_for('projects.edit_project_form', project_id=project_id))

@projects_bp.route('/project/<int:project_id>/toggle-visibility', methods=['POST'])
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
    
    try:
        with db_transaction():
            project.private = False
        flash("Il progetto è stato reso pubblico con successo.", "success")
    except Exception as exc:
        current_app.logger.error(f"Errore cambio visibilità progetto {project_id}: {exc}", exc_info=True)
        flash("Si è verificato un errore nel rendere pubblico il progetto.", "error")
        
    return redirect(url_for('projects.project_detail', project_id=project_id))

@projects_bp.route('/project/<int:project_id>/edit')
@login_required
def edit_project_form(project_id: int) -> Response | str:
    """Mostra il form per modificare un progetto esistente."""
    project = Project.query.get_or_404(project_id)
    
    # Verifica che l'utente sia il creatore del progetto
    if project.creator_id != current_user.id:
        flash("Non sei autorizzato a modificare questo progetto.", "error")
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    return render_template('edit_project.html',
                          project=project,
                          allowed_categories=ALLOWED_PROJECT_CATEGORIES)

@projects_bp.route('/project/<int:project_id>/update', methods=['POST'])
@login_required
def update_project(project_id: int) -> Response | str:
    """API per aggiornare un progetto."""
    print(f"DEBUG: update_project chiamato per project_id={project_id}")
    print(f"DEBUG: request.is_json={request.is_json}")
    print(f"DEBUG: request.form={dict(request.form)}")
    
    project = Project.query.get_or_404(project_id)
    
    # Verifica che l'utente sia il creatore del progetto
    if project.creator_id != current_user.id:
        print(f"DEBUG: Utente non autorizzato. Creator: {project.creator_id}, Current: {current_user.id}")
        if request.is_json:
            return jsonify({"error": "Non sei autorizzato a modificare questo progetto."}), 403
        else:
            flash("Non sei autorizzato a modificare questo progetto.", 'error')
            return redirect(url_for('projects.project_detail', project_id=project_id))
    
    # Verifica CSRF token per richieste JSON
    if request.is_json:
        csrf_token = request.headers.get('X-CSRF-Token')
        print(f"DEBUG: CSRF token nell'header: {csrf_token}")
        if csrf_token:
            try:
                validate_csrf(csrf_token)
                print("DEBUG: CSRF token validato con successo")
            except ValidationError as e:
                print(f"DEBUG: Errore validazione CSRF: {e}")
                return jsonify({"error": "Token CSRF non valido."}), 400
        else:
            print("DEBUG: CSRF token mancante nell'header")
            return jsonify({"error": "Token CSRF mancante."}), 400
    
    # Gestisci sia richieste JSON che form HTML
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    def validation_error_response(message: str):
        if request.is_json:
            return jsonify({"error": message}), 400
        flash(message, 'error')
        return redirect(url_for('projects.edit_project_form', project_id=project_id))
    
    try:
        if 'name' in data:
            data['name'] = clean_plain_text_field('project', 'name', data.get('name'))
        if 'pitch' in data:
            data['pitch'] = clean_plain_text_field('project', 'pitch', data.get('pitch'))
        if 'description' in data:
            data['description'] = clean_rich_text_field('project', 'description', data.get('description'))
    except ValueError as exc:
        return validation_error_response(str(exc))
    
    print(f"DEBUG: Dati ricevuti: {data}")
    
    # Valori prima dell'aggiornamento
    print(f"DEBUG: PRIMA - Nome: '{project.name}', Pitch: '{project.pitch}'")
    
    # Aggiorna i campi del progetto
    if 'name' in data:
        project.name = data['name']
    
    # Se il pitch viene modificato, resetta il rewritten_pitch per far prevalere quello manuale
    if 'pitch' in data:
        new_pitch = data['pitch']
        if new_pitch != project.pitch:
            project.pitch = new_pitch
            project.rewritten_pitch = None  # Resetta il rewritten_pitch per far prevalere quello manuale
            print("DEBUG: Pitch modificato - resetto rewritten_pitch")
    
    if 'description' in data:
        project.description = data['description']
    project.category = data.get('category', project.category)
    project.repository_url = data.get('repository_url', project.repository_url)
    
    print(f"DEBUG: DOPO - Nome: '{project.name}', Pitch: '{project.pitch}'")
    
    # Gestisci l'immagine di copertina - mantienila se non viene fornito un nuovo valore o è vuoto
    cover_image_url = data.get('cover_image_url')
    if cover_image_url is not None and cover_image_url.strip():
        project.cover_image_url = cover_image_url
    # Se è esplicitamente richiesto di rimuovere l'immagine
    elif 'remove_cover_image' in data and data.get('remove_cover_image'):
        project.cover_image_url = None
    
    # Gestisci il campo privato (solo se il progetto è già privato o non ha ancora collaboratori)
    private = data.get('private', project.private)
    
    # Un progetto pubblico non può diventare privato se ha già collaboratori
    if not project.private and private:
        collaborators_count = Collaborator.query.filter_by(project_id=project.id).count()
        if collaborators_count > 1:  # > 1 perché il creatore è anche un collaboratore
            if request.is_json:
                return jsonify({"error": "Non puoi rendere privato un progetto che ha già collaboratori."}), 400
            else:
                flash("Non puoi rendere privato un progetto che ha già collaboratori.", 'error')
                return redirect(url_for('projects.edit_project', project_id=project_id))
    
    project.private = private
    
    try:
        with db_transaction():
            pass
        if request.is_json:
            return jsonify({
                "success": True,
                "message": "Progetto aggiornato con successo!",
                "redirect_url": url_for('projects.project_detail', project_id=project.id)
            }), 200
        else:
            flash("Progetto aggiornato con successo!", 'success')
            return redirect(url_for('projects.project_detail', project_id=project.id))
    except Exception as e:
        current_app.logger.error(f"Errore nell'aggiornamento del progetto: {e}", exc_info=True)
        if request.is_json:
            return jsonify({"error": "Errore nell'aggiornamento del progetto."}), 500
        else:
            flash("Errore nell'aggiornamento del progetto.", 'error')
            return redirect(url_for('projects.edit_project', project_id=project_id))


@projects_bp.route('/projects/<int:project_id>/github-url', methods=['POST'])
@login_required
@role_required('project_id', roles=['creator'])
def update_github_url(project_id):
    """Aggiorna il repository GitHub del progetto"""
    try:
        data = request.get_json()
        github_url = data.get('github_url', '').strip()
        
        current_app.logger.info(f"Updating GitHub URL for project {project_id}: '{github_url}'")
        
        # Estrai il nome del repository dall'URL
        github_repo_name = None
        if github_url:
            # Validazione URL
            if not github_url.startswith('https://github.com/'):
                return jsonify({
                    'success': False,
                    'error': 'L\'URL deve essere un repository GitHub valido (https://github.com/...)'
                }), 400
            
            # Pulisci l'URL rimuovendo https://github.com/ e eventuali trailing slash
            clean_path = github_url.replace('https://github.com/', '').strip('/')
            current_app.logger.info(f"Clean path after removing domain: '{clean_path}'")
            
            # Estrai owner/repo da URL: owner/repo o owner/repo/...
            parts = [p for p in clean_path.split('/') if p]  # Rimuovi parti vuote
            current_app.logger.info(f"Parts after split: {parts}")
            
            if len(parts) >= 2:
                github_repo_name = f"{parts[0]}/{parts[1]}"
            else:
                current_app.logger.error(f"Not enough parts to extract owner/repo: {parts}")
        
        current_app.logger.info(f"Extracted repo name: '{github_repo_name}'")
        
        project = Project.query.get_or_404(project_id)
        with db_transaction():
            project.github_repo_name = github_repo_name
        
        current_app.logger.info(f"GitHub repo name saved successfully: {project.github_repo_name}")
        
        # Ricostruisci l'URL completo per la risposta
        full_url = f"https://github.com/{github_repo_name}" if github_repo_name else None
        
        return jsonify({
            'success': True,
            'message': 'Repository GitHub aggiornato con successo!',
            'github_url': full_url,
            'github_repo_name': github_repo_name
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Errore aggiornamento GitHub URL: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Errore interno del server'
        }), 500

@projects_bp.route('/project/<int:project_id>/download-zip')
@login_required
def download_project_zip(project_id):
    """
    Scarica il progetto come ZIP.
    Priorità:
    1. GitHub Repository (se collegato)
    2. Workspace Locale (se presente)
    """
    project = Project.query.get_or_404(project_id)
    
    # 1. Prova GitHub
    if project.github_repo_name:
        # Costruisci URL GitHub Archive
        repo_full_name = project.github_repo_name
        
        # Recupera token se disponibile
        github_token = current_app.config.get('GITHUB_TOKEN')
        headers = {}
        if github_token:
            headers['Authorization'] = f'token {github_token}'
            
        api_url = f"https://api.github.com/repos/{repo_full_name}/zipball"
        
        try:
            # Stream the response to avoid loading big files in memory
            req = requests.get(api_url, headers=headers, stream=True)
            
            if req.status_code == 200:
                return Response(
                    req.iter_content(chunk_size=1024*1024),
                    content_type=req.headers.get('Content-Type', 'application/zip'),
                    headers={
                        'Content-Disposition': f'attachment; filename={project.name.replace(" ", "_")}_source.zip'
                    }
                )
            else:
                current_app.logger.warning(f"GitHub Download Failed: {req.status_code} - Fallback to local workspace if available.")
        except Exception as e:
            current_app.logger.error(f"GitHub Download Exception: {str(e)}")

    # 2. Prova Workspace Locale
    local_repo_path = synced_repo_dir(project.id)
    if os.path.exists(local_repo_path) and os.listdir(local_repo_path):
        try:
            # Usa tempfile per creare lo zip
            temp_dir = tempfile.mkdtemp()
            zip_filename = f"{project.name.replace(' ', '_')}_workspace.zip"
            zip_base = os.path.join(temp_dir, project.name.replace(' ', '_'))
            
            shutil.make_archive(zip_base, 'zip', local_repo_path)
            zip_path = zip_base + '.zip'
            
            return send_file(
                zip_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name=zip_filename
            )
        except Exception as e:
            current_app.logger.error(f"Local ZIP Error: {str(e)}")
            flash('Errore durante la creazione dello ZIP locale.', 'error')
            return redirect(url_for('projects.project_detail', project_id=project_id))

    flash('Nessun codice sorgente disponibile per il download (né GitHub né Workspace).', 'error')
    return redirect(url_for('projects.project_detail', project_id=project_id))


from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, abort, Response, jsonify
from flask_login import login_required, current_user
from flask_wtf.csrf import validate_csrf, ValidationError
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from datetime import datetime

from .extensions import db
from .models import (
    Project, Task, Endorsement, Collaborator, ProjectVote,
    ALLOWED_PROJECT_CATEGORIES, ALLOWED_TASK_STATUS,
    ALLOWED_TASK_PHASES, ALLOWED_TASK_DIFFICULTIES, PROJECT_TYPES
)
from .forms import BaseForm
from .utils import calculate_project_equity
from .email_middleware import email_verification_required
from .decorators import role_required

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
    
    # Calcola le metriche reali
    projects_count = Project.query.filter_by(private=False).count()
    collaborators_count = Collaborator.query.count()
    
    # Conta tutti i task di progetti pubblici (task pubblici o senza flag is_private)
    public_tasks_count = Task.query.join(Project).filter(
        Project.private == False,
        db.or_(Task.is_private == False, Task.is_private == None)
    ).count()
    
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
                           allowed_categories=ALLOWED_PROJECT_CATEGORIES,
                           current_category=category,
                           current_project_type=project_type,  # Nuovo parametro
                           project_types=PROJECT_TYPES,       # Nuovo parametro
                           user_votes=user_votes)

@projects_bp.route('/create-project', methods=['GET', 'POST'])
@login_required
@email_verification_required
def create_project_form() -> Response | str:
    """Mostra il form per creare un nuovo progetto."""
    if request.method == 'POST':
        # Logica per gestire la creazione del progetto qui
        name = request.form.get('name')
        category = request.form.get('category')
        pitch = request.form.get('pitch')
        description = request.form.get('description')
        
        # --- NUOVO: SUPPORTO TIPO PROGETTO ---
        project_type = request.form.get('project_type', 'commercial')
        creator_equity = None
        
        # Solo progetti commerciali hanno equity
        if project_type == 'commercial':
            creator_equity = float(request.form.get('creator_equity', 5.0))
        
        new_project = Project(
            name=name,
            category=category,
            pitch=pitch,
            description=description,
            project_type=project_type,  # Nuovo campo
            creator_equity=creator_equity,  # Ora può essere None per ricerche scientifiche
            creator_id=current_user.id,
            platform_fee=1.0
        )
        db.session.add(new_project)
        db.session.commit()
        
        # 🎯 INITIALIZE CREATOR EQUITY (ProjectEquity system)
        try:
            from app.services.equity_service import EquityService
            equity_service = EquityService()
            equity_service.initialize_creator_equity(new_project)
            current_app.logger.info(f'Initialized creator equity for project {new_project.id} - User {current_user.id}')
        except Exception as e:
            current_app.logger.error(f'Failed to initialize creator equity for project {new_project.id}: {str(e)}')
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
                new_project.ai_mvp_guide = mvp_guide
                new_project.ai_feasibility_analysis = feasibility_analysis
                new_project.ai_guide_generated_at = datetime.now(timezone.utc)
                db.session.commit()
                flash('Progetto creato con successo! Le guide AI sono state generate automaticamente.', 'success')
            else:
                flash('Progetto creato con successo! Le guide AI saranno disponibili a breve.', 'info')
                
        except Exception as e:
            # Non bloccare la creazione del progetto se la generazione AI fallisce
            current_app.logger.error(f"Errore generazione guide AI: {str(e)}")
            flash('Progetto creato con successo!', 'success')
        
        # ========== NUOVO: GITHUB SYNC SETUP (AUTOMATICO) ==========
        # Se GitHub è abilitato globalmente, crea automaticamente il repository
        try:
            from app.services import GitHubSyncService
            sync_service = GitHubSyncService()
            
            if sync_service.is_enabled():
                # Setup repository automatico (nessuna checkbox, completamente trasparente)
                repo_info = sync_service.setup_project_repository(new_project)
                if repo_info:
                    current_app.logger.info(f"GitHub repository auto-created for project {new_project.id}")
                    # Nessun flash message - completamente silenzioso per l'utente
        except Exception as e:
            current_app.logger.warning(f"GitHub sync setup failed for project {new_project.id}: {e}")
            # Nessun messaggio all'utente - il progetto funziona comunque
        # ========== FINE GITHUB SYNC SETUP ==========
        
        return redirect(url_for('projects.project_detail', project_id=new_project.id))
    return render_template('create_project.html',
                           allowed_categories=ALLOWED_PROJECT_CATEGORIES,
                           project_types=PROJECT_TYPES)

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
    
    # Verifica accesso ai progetti privati
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
    
    # Correzione: Passa l'intero oggetto 'project'
    distributed_equity = calculate_project_equity(project)
    
    creator_equity = project.creator_equity
    distributed_equity = sum([c.equity_share for c in project.collaborators])
    platform_fee = getattr(project, 'platform_fee', 1.0)
    remaining_equity = 100 - creator_equity - distributed_equity - platform_fee

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

    all_completed_tasks = project.tasks.filter(Task.status.in_(['approved', 'closed'])).all()
    completed_tasks = [task for task in all_completed_tasks if task.can_view(current_user)]
    
    has_active_tasks = bool(active_tasks)

    collaborators = Collaborator.query.options(joinedload(Collaborator.user)).filter_by(project_id=project.id).order_by(Collaborator.equity_share.desc()).all()

    return render_template('project_detail.html',
                           project=project,
                           tasks_by_phase=tasks_by_phase,
                           completed_tasks=completed_tasks,
                           has_active_tasks=has_active_tasks,
                           collaborators=collaborators,
                           user_has_endorsed=user_has_endorsed,
                           user_has_voted_this_month=user_has_voted_this_month,
                           ALLOWED_TASK_STATUS=ALLOWED_TASK_STATUS,
                           ALLOWED_TASK_PHASES=ALLOWED_TASK_PHASES,
                           creator_equity=creator_equity,
                           distributed_equity=distributed_equity,
                           platform_fee=platform_fee,
                           remaining_equity=remaining_equity,
                           ALLOWED_TASK_DIFFICULTIES=ALLOWED_TASK_DIFFICULTIES,
                           form=form)


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
    
    # Rendi il progetto pubblico
    project.private = False
    
    try:
        db.session.commit()
        flash("Il progetto è stato reso pubblico con successo.", "success")
    except:
        db.session.rollback()
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
    
    print(f"DEBUG: Dati ricevuti: {data}")
    
    # Valori prima dell'aggiornamento
    print(f"DEBUG: PRIMA - Nome: '{project.name}', Pitch: '{project.pitch}'")
    
    # Aggiorna i campi del progetto
    project.name = data.get('name', project.name)
    
    # Se il pitch viene modificato, resetta il rewritten_pitch per far prevalere quello manuale
    new_pitch = data.get('pitch', project.pitch)
    if new_pitch != project.pitch:
        project.pitch = new_pitch
        project.rewritten_pitch = None  # Resetta il rewritten_pitch per far prevalere quello manuale
        print("DEBUG: Pitch modificato - resetto rewritten_pitch")
    
    project.description = data.get('description', project.description)
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
        db.session.commit()
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
        db.session.rollback()
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
        project.github_repo_name = github_repo_name
        
        db.session.commit()
        
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
        db.session.rollback()
        current_app.logger.error(f"Errore aggiornamento GitHub URL: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Errore interno del server'
        }), 500


# app/__init__.py

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from .config import Config
from .extensions import db, login_manager, mail
from flask_migrate import Migrate
from .routes_projects import projects_bp
from .routes_auth import auth_bp
from .routes_tasks import tasks_bp
from .routes_users import users_bp
from .routes_general import general_bp  # Importazione per pages generali
from .api_solutions import api_solutions_bp
from .api_projects import api_projects_bp
from .api_help import api_help_bp  # Nuova importazione per aiuto AI
from .routes_invites import invites_bp  # Nuova importazione
from .api_uploads import api_uploads_bp  # Nuova importazione per uploads
from .routes_wiki import wiki_bp  # Nuova importazione per la Wiki
from .routes_investments import investments_bp  # Nuova importazione per Investimenti
from .routes_health import health_bp  # Health check endpoint
# NOTE: free_proposals_bp importato dentro create_app() per evitare problemi nei test
from . import errors
from . import utils

csrf = CSRFProtect()


def setup_logging(app):
    """
    Configura il sistema di logging strutturato con RotatingFileHandler.
    
    - In development: DEBUG level, logs su console e file
    - In production: INFO level, logs su file con rotazione
    - Formato: timestamp | level | pathname:lineno | message
    """
    # Determina il livello di log dalla configurazione
    log_level_name = app.config.get('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Rimuovi handler esistenti per evitare duplicati
    if app.logger.handlers:
        app.logger.handlers.clear()
    
    # Formato dettagliato per i log
    log_format = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(pathname)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ============================================
    # Console Handler (sempre attivo in development)
    # ============================================
    if app.config.get('FLASK_ENV') != 'production':
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(log_format)
        app.logger.addHandler(console_handler)
    
    # ============================================
    # File Handler con rotazione
    # ============================================
    log_file = app.config.get('LOG_FILE', 'logs/app.log')
    log_dir = os.path.dirname(log_file)
    
    # Crea directory logs se non esiste
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            app.logger.error(f"Failed to create logs directory: {e}")
            # In caso di errore, logga solo su console
            return
    
    try:
        # RotatingFileHandler: max 10MB per file, mantieni 10 backup
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=app.config.get('LOG_MAX_BYTES', 10 * 1024 * 1024),  # 10MB
            backupCount=app.config.get('LOG_BACKUP_COUNT', 10)
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_format)
        app.logger.addHandler(file_handler)
    except Exception as e:
        app.logger.error(f"Failed to setup file logging: {e}")
    
    # Imposta il livello del logger principale
    app.logger.setLevel(log_level)
    
    # Disabilita la propagazione al logger root di Flask per evitare duplicati
    app.logger.propagate = False
    
    # Log iniziale per confermare configurazione
    app.logger.info(
        f"Logging configured: Level={log_level_name}, "
        f"File={log_file}, "
        f"Console={'Yes' if app.config.get('FLASK_ENV') != 'production' else 'No'}"
    )
    
    # ============================================
    # Configura logging per librerie di terze parti
    # ============================================
    # Riduci verbosità di werkzeug (server HTTP di Flask)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    # SQLAlchemy logging (utile per debugging query in development)
    if app.config.get('FLASK_ENV') != 'production':
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    else:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

def create_app(config_class=Config):
    """
    Application Factory per creare e configurare l'istanza dell'app Flask.
    """
    app = Flask(__name__)
    
    # Se config_class è un dizionario (per i test), lo usiamo direttamente
    if isinstance(config_class, dict):
        app.config.update(config_class)
    else:
        app.config.from_object(config_class)
    
    # ============================================
    # STRUCTURED LOGGING CONFIGURATION
    # ============================================
    setup_logging(app)
    
    # Validate production configuration if in production mode
    if app.config.get('FLASK_ENV') == 'production':
        try:
            config_class.validate_production_config()
        except ValueError as e:
            app.logger.error(f"Production configuration validation failed: {e}")
            # In production, we should fail fast if config is invalid
            raise
    
    app.logger.info(f"Application starting in {app.config.get('FLASK_ENV', 'development')} mode")

    # Inizializza le estensioni con l'app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    migrate = Migrate(app, db)

    # Inizializza Flask-Limiter con configurazione da config.py
    from .extensions import limiter
    # Configura storage URI e default limits
    app.config.setdefault('RATELIMIT_STORAGE_URL', 'memory://')
    app.config.setdefault('RATELIMIT_DEFAULT', '200 per day;50 per hour')
    limiter.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Effettua il login per accedere a questa pagina.'
    
    # Aggiungi funzioni al contesto globale di Jinja2
    app.jinja_env.globals.update(get_pending_invite=utils.get_pending_invite)

    # Registra le Blueprints
    from .routes_notifications import notifications_bp
    from .api_ai_wiki import api_ai_wiki
    from .api_ai_projects import api_ai_projects
    from .routes_free_proposals import free_proposals_bp  # Import qui per evitare problemi nei test
    from .api_free_proposals import api_free_proposals_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(projects_bp, url_prefix='/')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(general_bp, url_prefix='/')  # Registrazione blueprint pagine generali
    app.register_blueprint(api_solutions_bp, url_prefix='/api')
    app.register_blueprint(api_projects_bp, url_prefix='/api')
    app.register_blueprint(api_free_proposals_bp, url_prefix='/api')
    app.register_blueprint(api_help_bp, url_prefix='/')  # Registrazione blueprint aiuto AI
    app.register_blueprint(notifications_bp, url_prefix='/')
    app.register_blueprint(invites_bp, url_prefix='/')  # Registrazione blueprint inviti
    app.register_blueprint(api_uploads_bp, url_prefix='/api')  # Registrazione blueprint uploads
    app.register_blueprint(wiki_bp, url_prefix='/')  # Registrazione blueprint wiki
    app.register_blueprint(investments_bp, url_prefix='/')  # Registrazione blueprint investimenti
    app.register_blueprint(health_bp, url_prefix='/')  # Health check endpoints
    app.register_blueprint(api_ai_wiki, url_prefix='/api')  # AI Wiki functionality
    app.register_blueprint(api_ai_projects, url_prefix='/api')  # AI Project guides
    app.register_blueprint(free_proposals_bp, url_prefix='/')  # Free proposals

    # Registra i gestori di errore
    app.register_error_handler(401, errors.unauthorized_error)
    app.register_error_handler(403, errors.forbidden_error)
    app.register_error_handler(404, errors.not_found_error)
    app.register_error_handler(429, errors.rate_limit_error)  # Rate limiting errors
    app.register_error_handler(500, errors.internal_error)

    # Registra i filtri Jinja2 e altri helper
    utils.register_helpers(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return db.session.get(User, int(user_id))

    # Inizializza middleware email
    from .email_middleware import init_email_middleware
    init_email_middleware(app)

    with app.app_context():
        # Crea tabelle solo se non esistono già o se esplicitamente richiesto
        try:
            from .models import User
            # Test se il database è già inizializzato
            db.session.execute(db.text("SELECT 1 FROM user LIMIT 1"))
        except Exception:
            # Le tabelle non esistono, le creiamo
            db.create_all()
            print("Database tables created successfully")

    return app

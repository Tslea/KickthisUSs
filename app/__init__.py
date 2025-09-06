# app/__init__.py

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
from . import errors
from . import utils

csrf = CSRFProtect()

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

    # Inizializza le estensioni con l'app
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    migrate = Migrate(app, db)

    # Inizializza Flask-Limiter
    from .extensions import limiter
    limiter.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Effettua il login per accedere a questa pagina.'
    
    # Aggiungi funzioni al contesto globale di Jinja2
    app.jinja_env.globals.update(get_pending_invite=utils.get_pending_invite)

    # Registra le Blueprints
    from .routes_notifications import notifications_bp
    from .api_ai_wiki import api_ai_wiki
    from .api_ai_projects import api_ai_projects
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(projects_bp, url_prefix='/')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(general_bp, url_prefix='/')  # Registrazione blueprint pagine generali
    app.register_blueprint(api_solutions_bp, url_prefix='/api')
    app.register_blueprint(api_projects_bp, url_prefix='/api')
    app.register_blueprint(api_help_bp, url_prefix='/')  # Registrazione blueprint aiuto AI
    app.register_blueprint(notifications_bp, url_prefix='/')
    app.register_blueprint(invites_bp, url_prefix='/')  # Registrazione blueprint inviti
    app.register_blueprint(api_uploads_bp, url_prefix='/api')  # Registrazione blueprint uploads
    app.register_blueprint(wiki_bp, url_prefix='/')  # Registrazione blueprint wiki
    app.register_blueprint(investments_bp, url_prefix='/')  # Registrazione blueprint investimenti
    app.register_blueprint(health_bp, url_prefix='/')  # Health check endpoints
    app.register_blueprint(api_ai_wiki, url_prefix='/api')  # AI Wiki functionality
    app.register_blueprint(api_ai_projects, url_prefix='/api')  # AI Project guides

    # Registra i gestori di errore
    app.register_error_handler(401, errors.unauthorized_error)
    app.register_error_handler(403, errors.forbidden_error)
    app.register_error_handler(404, errors.not_found_error)
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

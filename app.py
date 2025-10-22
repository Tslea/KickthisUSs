import os
from flask import Flask
from config.github_config import GITHUB_ENABLED

def create_app():
    app = Flask(__name__)
    
    # Configurazione dell'applicazione
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')
    app.config['DEBUG'] = os.getenv('DEBUG', 'true') == 'true'
    
    # NUOVA SEZIONE: Configurazione Celery per task asincroni
    if GITHUB_ENABLED:
        app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        app.config['CELERY_RESULT_BACKEND'] = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
        
        from tasks import init_celery
        init_celery(app)
        
        app.logger.info("GitHub integration enabled")
    else:
        app.logger.info("GitHub integration disabled")
    
    # Registrazione dei blueprint
    from auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from main import main_bp
    app.register_blueprint(main_bp)
    
    # NUOVA SEZIONE: Registra API blueprint
    if GITHUB_ENABLED:
        from api.github_viewer import api_github_bp
        app.register_blueprint(api_github_bp)
    
    return app
from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# Load broker URL from environment or use SQLite default
broker_url = os.environ.get('CELERY_BROKER_URL', 'sqla+sqlite:///instance/celery_broker.db')
result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'db+sqlite:///instance/celery_results.db')

celery = Celery(
    __name__,
    broker=broker_url,
    backend=result_backend
)

# Set default config
celery.conf.update(
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone='Europe/Rome'
)

def init_celery(app):
    """Initialize Celery with Flask app context"""
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# Import task modules to register them with Celery
from . import github_tasks  # noqa: F401, E402

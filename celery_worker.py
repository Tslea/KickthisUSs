"""
Celery worker per eseguire task asincroni GitHub
Esegui con: celery -A celery_worker.celery worker --loglevel=info
"""
from app import create_app
from tasks import celery, init_celery

flask_app = create_app()
init_celery(flask_app)

# Import task modules
import tasks.github_tasks

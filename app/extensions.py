# app/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Crea le istanze delle estensioni qui, senza inizializzarle

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

# Flask-Limiter per rate limiting
# Configurazione sarà letta da config.py (RATELIMIT_STORAGE_URL e RATELIMIT_DEFAULT)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=None,  # Sarà impostato da app.config in init_app()
    default_limits=[]  # Sarà impostato da app.config in init_app()
)

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
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

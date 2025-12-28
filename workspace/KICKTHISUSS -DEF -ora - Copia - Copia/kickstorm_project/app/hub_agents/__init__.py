from flask import Blueprint

hub_agents_bp = Blueprint('hub_agents', __name__, url_prefix='/hub-agents')

from . import routes

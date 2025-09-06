# app/routes_general.py

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy.orm import joinedload
from .models import Activity

general_bp = Blueprint('general', __name__, template_folder='templates')

@general_bp.route('/feed')
@login_required
def activity_feed():
    """Mostra un feed delle attività recenti sulla piattaforma."""
    activities = Activity.query.options(
        joinedload(Activity.user),
        joinedload(Activity.project)
    ).order_by(Activity.timestamp.desc()).limit(50).all()
    return render_template('feed.html', activities=activities)

# --- NUOVA ROUTE PER L'ECONOMIA DELLA PIATTAFORMA ---
@general_bp.route('/platform-economy')
def platform_economy():
    """Mostra la pagina che spiega il funzionamento dell'equity virtuale."""
    return render_template('platform_economy.html')

# --- ROUTE PER "COME FUNZIONA" ---
@general_bp.route('/come-funziona')
def how_it_works():
    """Mostra la pagina che spiega come funziona la piattaforma."""
    return render_template('how_it_works.html')

# --- ROUTE PER TERMINI DI SERVIZIO ---
@general_bp.route('/termini-di-servizio')
def terms_of_service():
    """Mostra la pagina dei termini di servizio."""
    return render_template('terms_of_service.html')

# --- ROUTE PER PRIVACY POLICY ---
@general_bp.route('/privacy-policy')
def privacy_policy():
    """Mostra la pagina della privacy policy."""
    return render_template('privacy_policy.html')

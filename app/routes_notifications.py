# app/routes_notifications.py

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .models import Notification
from .extensions import db

notifications_bp = Blueprint('notifications_bp', __name__, template_folder='templates')

@notifications_bp.route('/notifications')
@login_required
def notifications_list():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    return render_template('notifications.html', notifications=notifications)

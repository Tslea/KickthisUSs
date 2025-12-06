# app/routes_notifications.py

from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from .models import Notification
from .extensions import db
from .services.notification_service import NotificationService

notifications_bp = Blueprint('notifications_bp', __name__, template_folder='templates')

@notifications_bp.route('/notifications')
@login_required
def notifications_list():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@notifications_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Marca tutte le notifiche come lette (route per form HTML)"""
    try:
        count = NotificationService.mark_all_as_read(current_user.id)
        if count > 0:
            flash(f'{count} notifiche segnate come lette.', 'success')
        else:
            flash('Non ci sono notifiche da segnare come lette.', 'info')
    except Exception as e:
        flash('Errore durante l\'operazione.', 'error')
    
    return redirect(url_for('notifications_bp.notifications_list'))

@notifications_bp.route('/api/notifications/unread-count')
@login_required
def unread_count():
    """API endpoint per ottenere il numero di notifiche non lette"""
    count = NotificationService.get_unread_count(current_user.id)
    return jsonify({'count': count})

@notifications_bp.route('/api/notifications/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Marca una notifica come letta (API endpoint)"""
    success = NotificationService.mark_as_read(notification_id, current_user.id)
    return jsonify({'success': success})

@notifications_bp.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_read_api():
    """Marca tutte le notifiche come lette (API endpoint per AJAX)"""
    count = NotificationService.mark_all_as_read(current_user.id)
    return jsonify({'success': True, 'count': count})

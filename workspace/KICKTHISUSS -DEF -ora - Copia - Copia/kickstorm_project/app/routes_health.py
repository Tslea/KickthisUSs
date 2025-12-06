# app/routes_health.py

from flask import Blueprint, jsonify, current_app
from .extensions import db
from .models import User
import os
import time

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """
    Endpoint di health check per monitoring (UptimeRobot, etc.)
    """
    try:
        # Test database connectivity
        start_time = time.time()
        user_count = db.session.query(User).count()
        db_response_time = (time.time() - start_time) * 1000  # in ms
        
        # Basic app health
        health_data = {
            'status': 'healthy',
            'timestamp': int(time.time()),
            'database': {
                'status': 'connected',
                'users_count': user_count,
                'response_time_ms': round(db_response_time, 2)
            },
            'environment': os.getenv('FLASK_ENV', 'development'),
            'version': '1.0.0'
        }
        
        return jsonify(health_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': int(time.time()),
            'error': str(e),
            'database': {'status': 'disconnected'}
        }), 503

@health_bp.route('/health/simple')
def simple_health():
    """
    Endpoint semplice per check rapidi
    """
    return jsonify({'status': 'ok'}), 200

@health_bp.route('/health/ready')
def readiness_check():
    """
    Readiness check per Kubernetes/Cloud Run
    """
    try:
        # Test critical services
        db.session.execute(db.text("SELECT 1"))
        return jsonify({'ready': True}), 200
    except Exception:
        return jsonify({'ready': False}), 503

@health_bp.route('/health/live')
def liveness_check():
    """
    Liveness check - applicazione è viva
    """
    return jsonify({'alive': True}), 200

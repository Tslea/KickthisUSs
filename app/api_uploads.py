# app/api_uploads.py
import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

api_uploads_bp = Blueprint('api_uploads', __name__)

# Estensioni di file consentite per le immagini
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    """Verifica se il file ha un'estensione consentita."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_unique_filename(filename):
    """Genera un nome di file univoco per evitare sovrascritture."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    random_uuid = uuid.uuid4().hex
    return f"{random_uuid}.{ext}" if ext else random_uuid

@api_uploads_bp.route('/upload-image', methods=['POST'])
@login_required
def upload_image():
    """Endpoint API per caricare un'immagine."""
    # Verifica se esiste una directory uploads, altrimenti la crea
    upload_folder = os.path.join(current_app.static_folder, 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Nessun file caricato'
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Nessun file selezionato'
        }), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = get_unique_filename(filename)
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Restituisci l'URL dell'immagine
        relative_path = f"/static/uploads/{unique_filename}"
        
        return jsonify({
            'success': True,
            'file': {
                'url': relative_path,
                'filename': unique_filename
            }
        }), 200
    
    return jsonify({
        'success': False,
        'error': 'Formato file non supportato. Formati supportati: ' + ', '.join(ALLOWED_EXTENSIONS)
    }), 400

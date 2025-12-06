import json
import mimetypes
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app
from itsdangerous import URLSafeTimedSerializer

# 🔒 SECURITY: File sensibili da bloccare sempre
BLOCKED_FILES = {
    '.env',
    '.env.local',
    '.env.production',
    '.env.development',
    '.env.test',
    '.git',
    'id_rsa',
    'id_ed25519',
    'id_dsa',
    '.pem',
    'secrets.yml',
    'credentials.json',
    '.aws',
    '.ssh',
    'config.json',  # Spesso contiene secrets
}

BLOCKED_EXTENSIONS = {
    '.key',
    '.pfx',
    '.p12',
    '.keystore',
    '.jks',
    '.der',
    '.crt',  # Certificati
    '.pem',  # Certificati PEM
}

BLOCKED_PATTERNS = [
    '__pycache__',
    '.pyc',
    'node_modules',
    '.DS_Store',
    'Thumbs.db',
    '.venv',
    'venv',
    '.idea',
    '.vscode/settings.json',  # Può contenere path assoluti
    '.ssh/',  # SSH config folder
    '.aws/',  # AWS credentials folder
]


def is_file_safe(filename: str) -> Tuple[bool, str]:
    """
    Verifica se un file può essere estratto/uploadato in sicurezza.
    
    Args:
        filename: Path del file (può essere relativo o assoluto)
    
    Returns:
        Tuple[bool, str]: (is_safe, reason)
    """
    # Normalizza il path
    name = os.path.basename(filename).lower()
    full_path = filename.lower().replace('\\', '/')
    
    # 1. Blocca file sensibili specifici
    if name in BLOCKED_FILES:
        return False, f"File sensibile bloccato: {name}"
    
    # 2. Blocca estensioni pericolose
    if any(name.endswith(ext) for ext in BLOCKED_EXTENSIONS):
        return False, f"Estensione pericolosa: {name}"
    
    # 3. Blocca pattern pericolosi
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in full_path:
            return False, f"Pattern bloccato: {pattern}"
    
    # 4. Blocca path traversal
    if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
        return False, "Path traversal rilevato"
    
    # 5. Blocca file nascosti sensibili (tranne .gitignore, .dockerignore)
    if name.startswith('.') and name not in ['.gitignore', '.dockerignore', '.editorconfig']:
        return False, f"File nascosto bloccato: {name}"
    
    return True, "OK"


# 🔒 SYNC BLACKLIST: Cartelle/file da NON sincronizzare MAI su GitHub
SYNC_BLACKLIST_DIRS = {
    '__pycache__',
    '.pytest_cache',
    'venv',
    '.venv',
    'env',
    'ENV',
    '.env',
    'node_modules',
    'bower_components',
    '.idea',
    '.vscode',
    '.git',
    'dist',
    'build',
    '.egg-info',
    'logs',
    '.mypy_cache',
    '.tox',
    'htmlcov',
    '.coverage',
    'instance',  # Flask instance folder (può contenere DB)
}

SYNC_BLACKLIST_FILES = {
    '.DS_Store',
    'Thumbs.db',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '*.so',
    '*.dll',
    '*.dylib',
    '*.log',
    '*.db',
    '*.sqlite',
    '*.sqlite3',
    '.env*',
    'secrets.*',
    'credentials.*',
    '*.key',
    '*.pem',
    '*.p12',
    '*.pfx',
}

def should_sync_to_github(file_path: str) -> Tuple[bool, str]:
    """
    Determina se un file deve essere sincronizzato su GitHub.
    Filtra file temporanei, build artifacts, virtual environments, secrets.
    
    Args:
        file_path: Path relativo del file
    
    Returns:
        Tuple[bool, str]: (should_sync, reason)
    """
    import fnmatch
    from pathlib import Path
    
    path = Path(file_path)
    parts = path.parts
    filename = path.name.lower()
    
    # 1. Blocca cartelle blacklisted
    for part in parts:
        if part in SYNC_BLACKLIST_DIRS:
            return False, f"Cartella ignorata: {part}"
    
    # 2. Blocca file/pattern blacklisted
    for pattern in SYNC_BLACKLIST_FILES:
        if '*' in pattern:
            if fnmatch.fnmatch(filename, pattern):
                return False, f"Pattern ignorato: {pattern}"
        elif filename == pattern.lower():
            return False, f"File ignorato: {pattern}"
    
    # 3. Verifica sicurezza generale (usa is_file_safe)
    is_safe, safety_reason = is_file_safe(file_path)
    if not is_safe:
        return False, f"Sicurezza: {safety_reason}"
    
    return True, "OK"


def get_workspace_root() -> str:
    root = current_app.config.get('PROJECT_WORKSPACE_ROOT')
    if not root:
        root = os.path.join(current_app.instance_path, 'project_uploads')
    os.makedirs(root, exist_ok=True)
    return root


def ensure_project_workspace(project_id: int) -> str:
    workspace = os.path.join(get_workspace_root(), str(project_id))
    incoming = os.path.join(workspace, 'incoming')
    os.makedirs(incoming, exist_ok=True)
    return workspace


def session_dir(project_id: int, session_id: str) -> str:
    workspace = ensure_project_workspace(project_id)
    directory = os.path.join(workspace, 'incoming', session_id)
    os.makedirs(directory, exist_ok=True)
    return directory


def synced_repo_dir(project_id: int) -> str:
    workspace = ensure_project_workspace(project_id)
    repo_dir = os.path.join(workspace, 'repo')
    os.makedirs(repo_dir, exist_ok=True)
    return repo_dir


def metadata_path(session_directory: str) -> str:
    return os.path.join(session_directory, 'metadata.json')


def load_session_metadata(session_directory: str) -> dict:
    path = metadata_path(session_directory)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as fp:
            return json.load(fp)
    return {}


def save_session_metadata(session_directory: str, data: dict):
    path = metadata_path(session_directory)
    os.makedirs(session_directory, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def default_metadata(session_id: str, project_id: int, upload_type: str) -> dict:
    return {
        'session_id': session_id,
        'project_id': project_id,
        'type': upload_type,
        'status': 'pending',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'files': [],
        'total_size': 0
    }


def history_file(project_id: int) -> str:
    workspace = ensure_project_workspace(project_id)
    return os.path.join(workspace, 'history.json')


def load_history_entries(project_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    path = history_file(project_id)
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as fp:
        try:
            data = json.load(fp)
        except json.JSONDecodeError:
            data = []
    if not isinstance(data, list):
        data = []
    if limit:
        return data[:limit]
    return data


def append_history_entry(project_id: int, entry: Dict[str, Any], max_entries: int = 20):
    history = load_history_entries(project_id)
    entry = dict(entry)
    entry.setdefault('created_at', datetime.now(timezone.utc).isoformat())
    history.insert(0, entry)
    history = history[:max_entries]
    path = history_file(project_id)
    with open(path, 'w', encoding='utf-8') as fp:
        json.dump(history, fp, ensure_ascii=False, indent=2)


def list_session_metadata(project_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    incoming_dir = os.path.join(ensure_project_workspace(project_id), 'incoming')
    if not os.path.exists(incoming_dir):
        return []

    sessions: List[Dict[str, Any]] = []
    for session_id in os.listdir(incoming_dir):
        session_path = os.path.join(incoming_dir, session_id)
        if not os.path.isdir(session_path):
            continue
        metadata = load_session_metadata(session_path)
        if metadata:
            # Auto-recovery: se una sessione è in "syncing" da più di 5 minuti, la marchia come "error"
            if metadata.get('status') == 'syncing':
                updated_at = metadata.get('updated_at') or metadata.get('created_at')
                if updated_at:
                    try:
                        from datetime import datetime, timezone, timedelta
                        updated_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        time_diff = now - updated_time
                        
                        # Se è passato più di 5 minuti, segna come errore
                        if time_diff > timedelta(minutes=5):
                            metadata['status'] = 'error'
                            metadata['error'] = 'Sync timeout - sessione bloccata recuperata automaticamente'
                            metadata['recovered_at'] = now.isoformat()
                            save_session_metadata(session_path, metadata)
                            current_app.logger.warning(
                                "Session %s auto-recovered from stuck 'syncing' state (age: %s)",
                                session_id, time_diff
                            )
                    except Exception as e:
                        current_app.logger.error("Error checking session timeout: %s", e)
            
            sessions.append(metadata)

    sessions.sort(key=lambda item: item.get('created_at', ''), reverse=True)
    if limit:
        return sessions[:limit]
    return sessions


def sanitize_workspace_path(relative_path: str) -> str:
    if not relative_path:
        raise ValueError("Il percorso relativo è obbligatorio.")
    parts = [part for part in relative_path.strip().split('/') if part not in ('', '.', '..')]
    if not parts:
        raise ValueError("Percorso relativo non valido.")
    sanitized = '/'.join(parts)
    return sanitized


def get_repo_file_path(project_id: int, relative_path: str) -> str:
    sanitized = sanitize_workspace_path(relative_path)
    repo_dir = synced_repo_dir(project_id)
    absolute_path = os.path.join(repo_dir, *sanitized.split('/'))
    if not os.path.realpath(absolute_path).startswith(os.path.realpath(repo_dir)):
        raise ValueError("Percorso non valido.")
    return absolute_path


def list_repo_files(project_id: int, limit: int = 500) -> List[Dict[str, Any]]:
    repo_dir = synced_repo_dir(project_id)
    if not os.path.exists(repo_dir):
        return []

    files: List[Dict[str, Any]] = []
    for root, _, filenames in os.walk(repo_dir):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            relative = os.path.relpath(full_path, repo_dir).replace('\\', '/')
            try:
                sanitized = sanitize_workspace_path(relative)
            except ValueError:
                continue
            size = os.path.getsize(full_path)
            mime, _ = mimetypes.guess_type(filename)
            files.append({
                'path': sanitized,
                'size': size,
                'mime': mime
            })
            if len(files) >= limit:
                break
        if len(files) >= limit:
            break

    files.sort(key=lambda item: item['path'])
    return files


def _file_token_serializer() -> URLSafeTimedSerializer:
    secret = current_app.config['SECRET_KEY']
    salt = current_app.config.get('WORKSPACE_FILE_TOKEN_SALT', 'workspace-file-token')
    return URLSafeTimedSerializer(secret_key=secret, salt=salt)


def generate_file_token(project_id: int, relative_path: str) -> str:
    serializer = _file_token_serializer()
    sanitized = sanitize_workspace_path(relative_path)
    return serializer.dumps({'project_id': project_id, 'path': sanitized})


def verify_file_token(token: str) -> Dict[str, Any]:
    serializer = _file_token_serializer()
    max_age = current_app.config.get('WORKSPACE_FILE_TOKEN_MAX_AGE', 300)
    return serializer.loads(token, max_age=max_age)


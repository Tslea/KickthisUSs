import os
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-super-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///dev.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    PROJECT_WORKSPACE_MAX_ZIP_MB = int(os.environ.get('PROJECT_WORKSPACE_MAX_ZIP_MB') or 500)
    PROJECT_WORKSPACE_MAX_FILE_MB = int(os.environ.get('PROJECT_WORKSPACE_MAX_FILE_MB') or 100)
    PROJECT_WORKSPACE_MAX_FILES = int(os.environ.get('PROJECT_WORKSPACE_MAX_FILES') or 5000)
    PROJECT_WORKSPACE_MAX_ZIP_BYTES = PROJECT_WORKSPACE_MAX_ZIP_MB * 1024 * 1024
    PROJECT_WORKSPACE_MAX_FILE_BYTES = PROJECT_WORKSPACE_MAX_FILE_MB * 1024 * 1024

    MAX_CONTENT_LENGTH = max(
        16 * 1024 * 1024,
        PROJECT_WORKSPACE_MAX_ZIP_BYTES,
        PROJECT_WORKSPACE_MAX_FILE_BYTES
    )
    PROJECT_WORKSPACE_ROOT = os.environ.get('PROJECT_WORKSPACE_ROOT') or os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance')),
        'project_uploads'
    )
    
    # Email Configuration (Gmail SMTP)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')  # Gmail address
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')  # App-specific password
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
    
    # Server URL for email links
    SERVER_URL = os.environ.get('SERVER_URL') or 'http://localhost:5000'

    # --- Sicurezza sessione Flask ---
    SESSION_COOKIE_SECURE = True  # Solo HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Non accessibile da JS
    SESSION_COOKIE_SAMESITE = 'Lax'  # Protezione CSRF
    PERMANENT_SESSION_LIFETIME = 3600  # 1 ora (in secondi)

    # Flask-Limiter (rate limiting)
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
    # ============================================
    # CACHING CONFIGURATION
    # ============================================
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')  # Use 'RedisCache' in production
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', 300))  # 5 minutes
    CACHE_REDIS_URL = os.environ.get('CACHE_REDIS_URL') or os.environ.get('REDIS_URL')
    
    # ============================================
    # GITHUB INTEGRATION
    # ============================================
    GITHUB_ENABLED = os.environ.get('GITHUB_ENABLED', 'false').lower() in ['true', 'on', '1']
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
    GITHUB_ORG = os.environ.get('GITHUB_ORG')
    GITHUB_DEFAULT_PRIVATE = os.environ.get('GITHUB_DEFAULT_PRIVATE', 'true').lower() in ['true', 'on', '1']

    # ============================================
    # AI CONFIGURATION
    # ============================================
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'deepseek')  # 'deepseek' or 'grok'
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    GROK_API_KEY = os.environ.get('GROK_API_KEY')
    
    # Model names
    DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
    GROK_MODEL = os.environ.get('GROK_MODEL', 'grok-4-fast')  # ← CAMBIO: grok-4-fast es el default

    # ============================================
    # PLATFORM SHARES CONFIGURATION (KickthisUSs)
    # ============================================
    # Platform user receives shares on every new project creation
    PLATFORM_USER_ID = int(os.environ.get('PLATFORM_USER_ID') or 0)  # 0 = disabled, set to actual user ID
    PLATFORM_SHARES_PERCENTAGE = float(os.environ.get('PLATFORM_SHARES_PERCENTAGE') or 5.0)  # 5% default
    CREATOR_SHARES_PERCENTAGE = float(os.environ.get('CREATOR_SHARES_PERCENTAGE') or 10.0)  # 10% default

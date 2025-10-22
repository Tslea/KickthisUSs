import os
import secrets
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class with security-first approach"""
    
    # ============================================
    # SECURITY SETTINGS - CRITICAL
    # ============================================
    
    # SECRET_KEY: MUST be set in production via environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        # In development, generate a random key but WARN
        SECRET_KEY = secrets.token_hex(32)
        print("⚠️  WARNING: SECRET_KEY not set! Using generated key (NOT for production!)")
        print(f"⚠️  Generated key: {SECRET_KEY}")
        print("⚠️  Set SECRET_KEY environment variable before deploying!")
    
    # Session configuration
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'  # HTTPS only in production
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    PERMANENT_SESSION_LIFETIME = 3600 * 24 * 7  # 7 days
    
    # ============================================
    # DATABASE SETTINGS
    # ============================================
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before using
        'pool_recycle': 3600,   # Recycle connections after 1 hour
        'pool_size': 10,        # Connection pool size
        'max_overflow': 20      # Max overflow connections
    }
    
    # ============================================
    # API KEYS - MUST be set via environment
    # ============================================
    
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    if not OPENAI_API_KEY and os.environ.get('FLASK_ENV') == 'production':
        raise ValueError("⚠️  OPENAI_API_KEY must be set in production!")
    
    # ============================================
    # EMAIL CONFIGURATION
    # ============================================
    
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # ============================================
    # FILE UPLOAD SECURITY
    # ============================================
    
    # Maximum file size: 16MB (increase for larger files if needed)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 
        'py', 'js', 'html', 'css', 'json', 'xml',
        'md', 'zip', 'tar', 'gz'
    }
    
    # MIME type validation (server-side, not just extension)
    ALLOWED_MIME_TYPES = {
        'text/plain', 'application/pdf',
        'image/png', 'image/jpeg', 'image/gif',
        'text/x-python', 'application/x-python-code',
        'text/javascript', 'application/javascript',
        'text/html', 'text/css',
        'application/json', 'application/xml',
        'text/markdown',
        'application/zip', 'application/x-tar', 'application/gzip'
    }
    
    # Upload folder (relative to instance folder)
    UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
    
    # ============================================
    # RATE LIMITING (Flask-Limiter)
    # ============================================
    
    # Redis connection for rate limiting (fallback to memory for development)
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
    
    # Default rate limits
    RATELIMIT_DEFAULT = "200 per day;50 per hour"  # General endpoints
    RATELIMIT_LOGIN = "5 per minute"  # Login endpoint (prevent brute force)
    RATELIMIT_API = "100 per hour"  # API endpoints
    RATELIMIT_UPLOAD = "10 per hour"  # File uploads
    
    # ============================================
    # GITHUB INTEGRATION
    # ============================================
    
    # GitHub OAuth (per login utenti - opzionale)
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
    
    # GitHub API Integration (per sincronizzazione repository)
    GITHUB_ENABLED = os.environ.get('GITHUB_ENABLED', 'false').lower() in ['true', 'on', '1']
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')  # Personal Access Token
    GITHUB_ORG = os.environ.get('GITHUB_ORG', 'kickthisuss-projects')  # Organization name
    GITHUB_DEFAULT_PRIVATE = os.environ.get('GITHUB_DEFAULT_PRIVATE', 'true').lower() in ['true', 'on', '1']
    
    # Template repository per nuovi progetti (opzionale)
    GITHUB_TEMPLATE_REPO = os.environ.get('GITHUB_TEMPLATE', None)
    
    if os.environ.get('FLASK_ENV') == 'production':
        if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
            print("⚠️  WARNING: GitHub OAuth not configured! GitHub login will not work.")
        if GITHUB_ENABLED and not GITHUB_TOKEN:
            print("⚠️  WARNING: GITHUB_TOKEN not set! GitHub repository sync will not work.")
    
    # ============================================
    # CSRF PROTECTION (WTForms)
    # ============================================
    
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # CSRF tokens valid for 1 hour
    WTF_CSRF_SSL_STRICT = os.environ.get('FLASK_ENV') == 'production'
    
    # ============================================
    # LOGGING CONFIGURATION
    # ============================================
    
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or ('INFO' if os.environ.get('FLASK_ENV') == 'production' else 'DEBUG')
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/app.log'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB per log file
    LOG_BACKUP_COUNT = 10  # Keep 10 backup log files
    
    # ============================================
    # VALIDATION METHOD
    # ============================================
    
    @staticmethod
    def validate_production_config():
        """
        Validates that all critical configuration is set for production.
        Call this in __init__.py when FLASK_ENV=production.
        """
        errors = []
        
        if not os.environ.get('SECRET_KEY'):
            errors.append("SECRET_KEY environment variable is not set!")
        
        if not os.environ.get('DATABASE_URL'):
            errors.append("DATABASE_URL not set - using SQLite is not recommended for production!")
        
        if not os.environ.get('OPENAI_API_KEY'):
            errors.append("OPENAI_API_KEY is not set - AI features will not work!")
        
        if not os.environ.get('MAIL_USERNAME') or not os.environ.get('MAIL_PASSWORD'):
            errors.append("Email credentials not set - email notifications will not work!")
        
        if errors:
            print("\n" + "=" * 60)
            print("⚠️  PRODUCTION CONFIGURATION ERRORS:")
            print("=" * 60)
            for error in errors:
                print(f"  ❌ {error}")
            print("=" * 60 + "\n")
            raise ValueError("Production configuration validation failed!")
        
        print("✅ Production configuration validated successfully!")
        return True
    
    @staticmethod
    def init_app(app):
        """Initialize application with this config"""
        # Ensure upload folder exists
        upload_path = os.path.join(app.instance_path, Config.UPLOAD_FOLDER)
        os.makedirs(upload_path, exist_ok=True)
        
        # Ensure logs folder exists
        log_dir = os.path.dirname(Config.LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

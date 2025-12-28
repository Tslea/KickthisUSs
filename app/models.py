# app/models.py

from .extensions import db
from flask_login import UserMixin
from datetime import datetime, timezone

# --- MODELLO NOTIFICHE ---
class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True, index=True)
    type = db.Column(db.String(50), nullable=False)  # 'solution_published', 'solution_approved', 'task_created'
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='notifications')
    project = db.relationship('Project', backref='notifications')

    def __repr__(self):
        return f"<Notification {self.type} to User {self.user_id}>"
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

# --- COSTANTI DEFINITE QUI ---
ALLOWED_PROJECT_CATEGORIES = {
    'Tech': 'Tecnologia e Software',
    'Art': 'Arte e Design',
    'Social': 'Sociale e No-Profit',
    'Business': 'Business e Finanza',
    'Education': 'Educazione',
    'Gaming': 'Videogiochi',
    'Other': 'Altro'
}

# --- NUOVO: TIPI DI PROGETTO ---
PROJECT_TYPES = {
    'commercial': '☀️ Startup',
    'scientific': '🔬 Ricerca Scientifica'
}

ALLOWED_TASK_TYPES = {
    'proposal': 'Proposta/Concept',
    'implementation': 'Implementazione',
    'validation': 'Esperimento di Validazione'
}

ALLOWED_TASK_PHASES = {
    'Planning': 'Pianificazione',
    'Research': 'Ricerca',
    'Design': 'Design',
    'Development': 'Sviluppo',
    'Testing': 'Test',
    'Marketing': 'Marketing'
}

ALLOWED_TASK_STATUS = {
    'suggested': "Suggerito (dall'IA)",
    'open': 'Aperto',
    'in_progress': 'In Corso',
    'submitted': 'Soluzione Proposta',
    'approved': 'Approvato',
    'closed': 'Chiuso'
}

ALLOWED_TASK_DIFFICULTIES = {
    'Very Easy': 'Molto Facile',
    'Easy': 'Facile',
    'Medium': 'Medio',
    'Hard': 'Difficile',
    'Very Hard': 'Molto Difficile'
}

# ⭐ NUOVO: TIPI DI CONTENUTO SUPPORTATI
CONTENT_TYPES = {
    'software': '💻 Software/Codice',
    'hardware': '🔧 Hardware/Elettronica',
    'design': '🎨 Design Grafico',
    'documentation': '📄 Documentazione',
    'media': '🎬 Media/Audio/Video',
    'mixed': '🔀 Misto'
}

# ⭐ NUOVO: CATEGORIE CONTENUTO PER TIPO
CONTENT_CATEGORIES = {
    'design': {
        'logo': 'Logo',
        'branding': 'Brand Identity',
        'mockup': 'UI/UX Mockup',
        'illustration': 'Illustrazione',
        'icon': 'Icona',
        'banner': 'Banner/Header',
        'infographic': 'Infografica',
        'typography': 'Typography/Font'
    },
    'documentation': {
        'user_guide': 'Guida Utente',
        'technical_doc': 'Documentazione Tecnica',
        'business_plan': 'Business Plan',
        'presentation': 'Presentazione',
        'whitepaper': 'Whitepaper',
        'tutorial': 'Tutorial',
        'api_doc': 'Documentazione API'
    },
    'media': {
        'video': 'Video',
        'audio': 'Audio/Podcast',
        'animation': 'Animazione',
        'photography': 'Fotografia',
        'promotional': 'Materiale Promozionale',
        'demo': 'Demo Video'
    },
    'hardware': {
        'schematic': 'Schema Elettrico',
        'pcb': 'PCB Design',
        'cad_3d': 'Modello 3D',
        'gerber': 'File Gerber',
        'bom': 'Bill of Materials',
        'assembly': 'Istruzioni Assemblaggio'
    },
    'software': {
        'source_code': 'Codice Sorgente',
        'library': 'Libreria',
        'plugin': 'Plugin/Estensione',
        'script': 'Script',
        'api': 'API',
        'framework': 'Framework'
    }
}


# --- MODELLI DATABASE ---

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_image_url = db.Column(db.String(2048), nullable=True)  # URL dell'immagine profilo
    
    # Email verification fields
    email_verified = db.Column(db.Boolean, default=False, nullable=True)  # Nullable per SQLite
    email_verification_token = db.Column(db.String(100), nullable=True)
    email_verification_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Password reset fields
    password_reset_token = db.Column(db.String(100), nullable=True)
    password_reset_sent_at = db.Column(db.DateTime, nullable=True)
    
    # 2FA fields
    totp_secret = db.Column(db.String(32), nullable=True)  # Secret per TOTP
    two_factor_enabled = db.Column(db.Boolean, default=False, nullable=False)  # Se 2FA è abilitato
    backup_codes = db.Column(db.Text, nullable=True)  # Codici di backup come JSON
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    projects = db.relationship('Project', back_populates='creator', lazy='dynamic', cascade='all, delete-orphan')
    created_tasks = db.relationship('Task', back_populates='creator', lazy='dynamic', foreign_keys='Task.creator_id') # Nuova relazione
    solutions = db.relationship('Solution', back_populates='submitter', lazy='dynamic', cascade='all, delete-orphan')
    collaborations = db.relationship('Collaborator', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('Activity', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    endorsements = db.relationship('Endorsement', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    votes = db.relationship('Vote', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

    def generate_email_verification_token(self):
        """Genera un token per la verifica email."""
        import secrets
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_sent_at = datetime.now(timezone.utc)
        return self.email_verification_token
    
    def verify_email(self):
        """Marca l'email come verificata."""
        self.email_verified = True
        self.email_verification_token = None
        self.email_verification_sent_at = None
    
    def generate_password_reset_token(self):
        """Genera un token per il reset password."""
        import secrets
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_sent_at = datetime.now(timezone.utc)
        return self.password_reset_token
    
    def reset_password(self, new_password):
        """Reset password e cancella il token."""
        self.set_password(new_password)
        self.password_reset_token = None
        self.password_reset_sent_at = None
    
    # --- 2FA Methods ---
    def generate_totp_secret(self):
        """Genera un nuovo secret TOTP."""
        import pyotp
        self.totp_secret = pyotp.random_base32()
        return self.totp_secret
    
    def get_totp_uri(self):
        """Ottiene l'URI per il QR code."""
        import pyotp
        if not self.totp_secret:
            return None
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.email,
            issuer_name="KickThisUss"
        )
    
    def verify_totp(self, token):
        """Verifica un token TOTP."""
        import pyotp
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token, valid_window=1)
    
    def generate_backup_codes(self):
        """Genera codici di backup per 2FA."""
        import secrets
        import json
        codes = [secrets.token_hex(4).upper() for _ in range(10)]
        self.backup_codes = json.dumps(codes)
        return codes
    
    def get_backup_codes(self):
        """Ottiene i codici di backup."""
        import json
        if not self.backup_codes:
            return []
        return json.loads(self.backup_codes)
    
    def use_backup_code(self, code):
        """Usa un codice di backup (lo rimuove dalla lista)."""
        import json
        codes = self.get_backup_codes()
        if code.upper() in codes:
            codes.remove(code.upper())
            self.backup_codes = json.dumps(codes)
            return True
        return False
    
    def enable_two_factor(self):
        """Abilita 2FA."""
        self.two_factor_enabled = True
    
    def disable_two_factor(self):
        """Disabilita 2FA e pulisce i dati correlati."""
        self.two_factor_enabled = False
        self.totp_secret = None
        self.backup_codes = None

    def __repr__(self):
        return f"<User {self.username}>"


# ============================================
# PHANTOM SHARES MODEL (NEW - Replaces Equity)
# ============================================
class PhantomShare(db.Model):
    """
    Tracks phantom shares (participation rights) for each user in a project.
    Phantom shares represent economic participation without legal ownership.
    More accessible and clear than "equity percentage" for normal users.
    
    Example: User has 1000 shares out of 10,000 total = 10% participation.
    If project earns €10,000, user receives €1,000.
    """
    __tablename__ = 'phantom_share'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Shares held (can be fractional, e.g., 0.5 shares)
    shares_count = db.Column(db.Numeric(20, 6), default=0.0, nullable=False)  # Using Decimal for precision
    
    # Track how shares were earned (for transparency)
    earned_from = db.Column(db.String(500), default='')  # Comma-separated: 'creator', 'task_123', 'bonus', 'investment'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('share_holders', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('project_shares', lazy='dynamic'))
    
    # Unique constraint: one share record per user per project
    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_id', name='_project_user_share_uc'),
    )
    
    def get_percentage(self):
        """Calculate percentage participation based on total shares in project"""
        if not self.project or not self.project.total_shares or self.project.total_shares == 0:
            return 0.0
        from decimal import Decimal
        return float((Decimal(str(self.shares_count)) / Decimal(str(self.project.total_shares))) * Decimal('100'))
    
    def __repr__(self):
        return f'<PhantomShare User {self.user_id} has {self.shares_count} shares in Project {self.project_id}>'


# ============================================
# EQUITY TRACKING MODEL (DEPRECATED - Keep for backward compatibility)
# ============================================
class ProjectEquity(db.Model):
    """
    Tracks individual equity ownership for each user in a project.
    This provides granular tracking of how equity is distributed
    through task completions, collaboration bonuses, etc.
    
    Note: Collaborator.equity_share still exists for backward compatibility,
    but ProjectEquity is the source of truth for detailed equity tracking.
    """
    __tablename__ = 'project_equity'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    equity_percentage = db.Column(db.Float, default=0.0, nullable=False)
    
    # Track how equity was earned (for transparency)
    earned_from = db.Column(db.String(500), default='')  # Comma-separated: 'creator', 'task_123', 'bonus'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('equity_holders', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('project_equities', lazy='dynamic'))
    
    # Unique constraint: one equity record per user per project
    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_id', name='_project_user_equity_uc'),
    )
    
    def __repr__(self):
        return f'<ProjectEquity {self.user.username} owns {self.equity_percentage}% of Project {self.project_id}>'


# ============================================
# SHARE HISTORY/AUDIT LOG MODEL (NEW - Replaces EquityHistory)
# ============================================
class ShareHistory(db.Model):
    """
    Audit log for all share changes (phantom shares).
    Tracks who got shares, when, why, and how much.
    Immutable records for compliance and transparency.
    """
    __tablename__ = 'share_history'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Change details
    action = db.Column(db.String(50), nullable=False, index=True)  # 'grant', 'revoke', 'transfer', 'adjust', 'initial'
    shares_change = db.Column(db.Numeric(20, 6), nullable=False)  # Positive for grant, negative for revoke
    shares_before = db.Column(db.Numeric(20, 6), nullable=False)  # Shares before change
    shares_after = db.Column(db.Numeric(20, 6), nullable=False)   # Shares after change
    
    # Percentage equivalents (for display)
    percentage_before = db.Column(db.Float, nullable=False)
    percentage_after = db.Column(db.Float, nullable=False)
    
    # Source of change
    reason = db.Column(db.String(500))  # Human-readable reason (e.g., "Task 123 completion", "Manual adjustment by creator")
    source_type = db.Column(db.String(50))  # 'task_completion', 'manual', 'bonus', 'initial', 'investment'
    source_id = db.Column(db.Integer)  # ID of related entity (task_id, solution_id, investment_id, etc.)
    
    # Who made the change (can be system/automated)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('share_history', lazy='dynamic', cascade='all, delete-orphan', order_by='ShareHistory.created_at.desc()'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('share_changes', lazy='dynamic'))
    changed_by = db.relationship('User', foreign_keys=[changed_by_user_id], backref=db.backref('share_changes_made', lazy='dynamic'))
    
    def __repr__(self):
        return f'<ShareHistory {self.action} {self.shares_change} shares for User {self.user_id} in Project {self.project_id}>'


# ============================================
# EQUITY HISTORY/AUDIT LOG MODEL (DEPRECATED - Keep for backward compatibility)
# ============================================
class EquityHistory(db.Model):
    """
    Audit log for all equity changes (DEPRECATED - Use ShareHistory instead).
    Kept for backward compatibility during migration.
    """
    __tablename__ = 'equity_history'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Change details
    action = db.Column(db.String(50), nullable=False, index=True)  # 'grant', 'revoke', 'transfer', 'adjust'
    equity_change = db.Column(db.Float, nullable=False)  # Positive for grant, negative for revoke
    equity_before = db.Column(db.Float, nullable=False)  # Equity before change
    equity_after = db.Column(db.Float, nullable=False)   # Equity after change
    
    # Source of change
    reason = db.Column(db.String(500))  # Human-readable reason (e.g., "Task 123 completion", "Manual adjustment by creator")
    source_type = db.Column(db.String(50))  # 'task_completion', 'manual', 'bonus', 'initial'
    source_id = db.Column(db.Integer)  # ID of related entity (task_id, solution_id, etc.)
    
    # Who made the change (can be system/automated)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('equity_history', lazy='dynamic', cascade='all, delete-orphan', order_by='EquityHistory.created_at.desc()'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('equity_changes', lazy='dynamic'))
    changed_by = db.relationship('User', foreign_keys=[changed_by_user_id], backref=db.backref('equity_changes_made', lazy='dynamic'))
    
    def __repr__(self):
        return f'<EquityHistory {self.action} {self.equity_change}% for User {self.user_id} in Project {self.project_id}>'


class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    pitch = db.Column(db.String(500))
    description = db.Column(db.Text)
    rewritten_pitch = db.Column(db.Text)
    cover_image_url = db.Column(db.String(2048))
    repository_url = db.Column(db.String(255), nullable=True) # --- CAMPO GENERICO REPOSITORY ---
    
    # --- GITHUB INTEGRATION (MINIMALE) ---
    # Solo il nome del repository - tutto il resto è gestito via GitHub API quando necessario
    github_repo_name = db.Column(db.String(100), nullable=True, index=True)  # es. "kickthisuss-projects/project-123"
    
    # AI-Generated Project Guide
    ai_mvp_guide = db.Column(db.Text, nullable=True)  # Guida step-by-step per MVP
    ai_feasibility_analysis = db.Column(db.Text, nullable=True)  # Analisi realistica possibilità
    ai_guide_generated_at = db.Column(db.DateTime, nullable=True)  # Timestamp generazione AI
    
    # --- NUOVO: SUPPORTO RICERCHE SCIENTIFICHE ---
    project_type = db.Column(db.String(20), nullable=False, default='commercial', index=True)  # 'commercial' o 'scientific'
    
    category = db.Column(db.String(50), nullable=False, index=True)
    creator_equity = db.Column(db.Float, nullable=True, default=5.0)  # Ora nullable per ricerche scientifiche
    platform_fee = db.Column(db.Float, nullable=False, default=1.0)
    
    # --- PHANTOM SHARES SYSTEM ---
    total_shares = db.Column(db.Numeric(20, 6), nullable=True)  # Total shares issued for this project (default: 10,000)
    # If total_shares is None, project uses old equity system (backward compatibility)
    
    status = db.Column(db.String(50), nullable=False, default='open', index=True)
    endorsement_count = db.Column(db.Integer, default=0, nullable=False)
    private = db.Column(db.Boolean, default=False, nullable=False)  # --- NUOVO CAMPO per progetti privati ---
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Add composite indexes for common query patterns
    __table_args__ = (
        db.Index('ix_project_private_created_at', 'private', 'created_at'),
        db.Index('ix_project_category_private', 'category', 'private'),
        db.Index('ix_project_type_private', 'project_type', 'private'),
    )
    
    creator = db.relationship('User', back_populates='projects')
    tasks = db.relationship('Task', back_populates='project', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='Task.project_id')
    collaborators = db.relationship('Collaborator', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('Activity', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    endorsements = db.relationship('Endorsement', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    repository = db.relationship('ProjectRepository', back_populates='project', uselist=False, cascade='all, delete-orphan')

    # --- PROPRIETÀ HELPER PER TIPO PROGETTO ---
    @property
    def is_scientific(self):
        """Verifica se è una ricerca scientifica"""
        return self.project_type == 'scientific'
    
    @property
    def is_commercial(self):
        """Verifica se è un progetto commerciale"""
        # Se project_type è None o vuoto, consideriamo il progetto come commerciale (default)
        return self.project_type == 'commercial' or self.project_type is None or self.project_type == ''
    
    @property 
    def project_type_display(self):
        """Restituisce il tipo di progetto in formato display"""
        if self.project_type == 'scientific':
            return '🔬 Ricerca Scientifica'
        else:
            # Default per commercial, None, o valori sconosciuti
            return '☀️ Startup'
    
    # ============================================
    # EQUITY MANAGEMENT METHODS
    # ============================================
    
    def get_total_equity_distributed(self):
        """
        Calculate total equity distributed to all users.
        Returns: float (sum of all equity percentages)
        """
        total = db.session.query(
            db.func.sum(ProjectEquity.equity_percentage)
        ).filter(ProjectEquity.project_id == self.id).scalar()
        return total or 0.0
    
    def get_available_equity(self):
        """
        Calculate remaining equity available for distribution.
        Uses EquityConfiguration if exists, otherwise assumes 100% total.
        """
        # Get equity configuration - handle both single object and list cases
        config = None
        if hasattr(self, 'equity_config') and self.equity_config:
            # If it's a list (InstrumentedList), take first element
            if hasattr(self.equity_config, '__iter__') and not isinstance(self.equity_config, (str, dict)):
                config = self.equity_config[0] if len(self.equity_config) > 0 else None
            else:
                config = self.equity_config
        
        if config and hasattr(config, 'team_percentage'):
            # Total distributable = team_percentage from config
            max_distributable = config.team_percentage
        else:
            # Fallback: assume 100% distributable (minus platform fee)
            max_distributable = 100.0 - self.platform_fee
        
        distributed = self.get_total_equity_distributed()
        available = max_distributable - distributed
        
        return max(0.0, available)  # Never return negative
    
    def can_distribute_equity(self, amount):
        """
        Check if specified equity amount can be distributed.
        
        Args:
            amount (float): Equity percentage to check
            
        Returns:
            bool: True if amount can be distributed
        """
        available = self.get_available_equity()
        return amount <= available
    
    # ============================================
    # PHANTOM SHARES MANAGEMENT METHODS (NEW)
    # ============================================
    
    def uses_shares_system(self):
        """Check if project uses new shares system (vs old equity system)"""
        return self.total_shares is not None and self.total_shares > 0
    
    def initialize_shares_system(self, total_shares=10000):
        """
        Initialize shares system for this project.
        Sets total_shares and creates initial shares for creator.
        
        Args:
            total_shares: Total shares to issue (default: 10,000)
        """
        from decimal import Decimal
        self.total_shares = Decimal(str(total_shares))
        db.session.flush()
    
    def get_total_shares_distributed(self):
        """
        Calculate total shares distributed to all users.
        Returns: Decimal (sum of all shares)
        """
        if not self.uses_shares_system():
            return None
        
        from decimal import Decimal
        from sqlalchemy import func
        total = db.session.query(
            func.sum(PhantomShare.shares_count)
        ).filter(PhantomShare.project_id == self.id).scalar()
        return Decimal(str(total)) if total else Decimal('0')
    
    def get_available_shares(self):
        """
        Calculate remaining shares available for distribution.
        Returns: Decimal (available shares)
        """
        if not self.uses_shares_system():
            return None
        
        from decimal import Decimal
        distributed = self.get_total_shares_distributed()
        available = Decimal(str(self.total_shares)) - distributed
        return max(Decimal('0'), available)
    
    def can_distribute_shares(self, shares_amount):
        """
        Check if specified shares amount can be distributed.
        
        Args:
            shares_amount: Shares to check (can be Decimal, float, or int)
            
        Returns:
            bool: True if shares can be distributed
        """
        if not self.uses_shares_system():
            return False
        
        from decimal import Decimal
        shares_decimal = Decimal(str(shares_amount))
        available = self.get_available_shares()
        return shares_decimal <= available
    
    def get_user_shares(self, user_id):
        """
        Get shares held by a specific user in this project.
        
        Args:
            user_id: User ID
            
        Returns:
            PhantomShare or None
        """
        if not self.uses_shares_system():
            return None
        return PhantomShare.query.filter_by(project_id=self.id, user_id=user_id).first()
    
    def get_user_shares_count(self, user_id):
        """
        Get number of shares held by a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            Decimal: Shares count, or 0 if none
        """
        from decimal import Decimal
        share_record = self.get_user_shares(user_id)
        if share_record:
            return Decimal(str(share_record.shares_count))
        return Decimal('0')
    
    def get_user_shares_percentage(self, user_id):
        """
        Get percentage participation for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            float: Percentage (0.0 to 100.0)
        """
        if not self.uses_shares_system() or not self.total_shares or self.total_shares == 0:
            return 0.0
        
        from decimal import Decimal
        shares_count = self.get_user_shares_count(user_id)
        total = Decimal(str(self.total_shares))
        if total == 0:
            return 0.0
        return float((shares_count / total) * Decimal('100'))
    
    def validate_equity_distribution(self):
        """
        Validate that total equity distributed doesn't exceed limits.
        
        Raises:
            ValueError: If equity distribution is invalid
            
        Returns:
            bool: True if valid
        """
        total = self.get_total_equity_distributed()
        
        # Get equity configuration - handle both single object and list cases
        config = None
        if hasattr(self, 'equity_config') and self.equity_config:
            # If it's a list (InstrumentedList), take first element
            if hasattr(self.equity_config, '__iter__') and not isinstance(self.equity_config, (str, dict)):
                config = self.equity_config[0] if len(self.equity_config) > 0 else None
            else:
                config = self.equity_config
        
        if config and hasattr(config, 'team_percentage'):
            max_allowed = config.team_percentage
            if total > max_allowed:
                raise ValueError(
                    f'Total equity distributed ({total}%) exceeds team allocation ({max_allowed}%)'
                )
        else:
            # Fallback validation: total shouldn't exceed 100% minus platform fee
            max_allowed = 100.0 - self.platform_fee
            if total > max_allowed:
                raise ValueError(
                    f'Total equity distributed ({total}%) exceeds maximum allowed ({max_allowed}%)'
                )
        
        return True
    
    def get_equity_distribution(self):
        """
        Get equity distribution as a dictionary.
        
        Returns:
            dict: {user_id: equity_percentage}
        """
        equity_records = ProjectEquity.query.filter_by(project_id=self.id).all()
        return {eq.user_id: eq.equity_percentage for eq in equity_records}
    
    def get_user_equity(self, user_id):
        """
        Get equity percentage for a specific user.
        
        Args:
            user_id (int): User ID
            
        Returns:
            float: Equity percentage (0.0 if user has no equity)
        """
        equity = ProjectEquity.query.filter_by(
            project_id=self.id,
            user_id=user_id
        ).first()
        return equity.equity_percentage if equity else 0.0

    def __repr__(self):
        return f"<Project {self.name} ({self.project_type})>"


class ProjectRepository(db.Model):
    __tablename__ = 'project_repository'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, unique=True, index=True)
    provider = db.Column(db.String(50), nullable=False, default='local', index=True)  # 'github_managed', 'local'
    repo_name = db.Column(db.String(255), nullable=True)
    branch = db.Column(db.String(100), nullable=False, default='main')
    status = db.Column(db.String(50), nullable=False, default='pending', index=True)  # 'pending', 'ready', 'disabled', 'error'
    last_sync_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    project = db.relationship('Project', back_populates='repository')
    
    @property
    def url(self):
        """Genera l'URL del repository basato sul provider e repo_name"""
        if not self.repo_name:
            return None
        if self.provider == 'github_managed':
            return f"https://github.com/{self.repo_name}"
        return None
    
    def mark_synced(self):
        self.status = 'ready'
        self.last_sync_at = datetime.now(timezone.utc)
    
    def __repr__(self):
        return f"<ProjectRepository project={self.project_id} provider={self.provider} status={self.status}>"

class Task(db.Model):
    __tablename__ = 'task'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True) 
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    equity_reward = db.Column(db.Float, nullable=False)
    task_type = db.Column(db.String(50), nullable=False, default='implementation', index=True) # --- NUOVO CAMPO ---
    status = db.Column(db.String(50), nullable=False, default='open', index=True)
    phase = db.Column(db.String(50), index=True)  # Add index for frequent filtering by phase
    difficulty = db.Column(db.String(50))
    is_suggestion = db.Column(db.Boolean, default=False)
    is_private = db.Column(db.Boolean, default=False, index=True)  # Add index for frequent filtering by visibility
    
    # Campi specifici per esperimenti di validazione
    hypothesis = db.Column(db.Text, nullable=True)  # Ipotesi da testare
    test_method = db.Column(db.Text, nullable=True)  # Metodo di test
    results = db.Column(db.Text, nullable=True)  # Risultati del test
    
    # GitHub Integration
    github_issue_number = db.Column(db.Integer, nullable=True)
    github_synced_at = db.Column(db.DateTime, nullable=True)
    
    # Add composite indexes for common query patterns
    __table_args__ = (
        db.Index('ix_task_project_status', 'project_id', 'status'),
        db.Index('ix_task_project_is_private', 'project_id', 'is_private'),
        db.Index('ix_task_project_status_is_private', 'project_id', 'status', 'is_private'),
    )
    
    project = db.relationship('Project', back_populates='tasks', foreign_keys=[project_id])
    creator = db.relationship('User', back_populates='created_tasks', foreign_keys=[creator_id]) 
    solutions = db.relationship('Solution', back_populates='task', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('Activity', back_populates='task', lazy='dynamic', cascade='all, delete-orphan')
    votes = db.relationship('Vote', back_populates='task', lazy='dynamic', cascade='all, delete-orphan')

    def can_view(self, user):
        """
        Determina se un utente può visualizzare questo task.
        - I task pubblici possono essere visti da tutti
        - I task privati solo dal creatore del progetto e dai collaboratori
        """
        if not self.is_private:
            return True
            
        if not user or not user.is_authenticated:
            return False
            
        # Il creatore del progetto può sempre vedere i task privati
        if self.project.creator_id == user.id:
            return True
            
        # I collaboratori possono vedere i task privati
        from sqlalchemy import and_
        collaborator = db.session.query(Collaborator).filter(
            and_(Collaborator.project_id == self.project_id,
                 Collaborator.user_id == user.id)
        ).first()
        
        return collaborator is not None

    @staticmethod
    def can_create_for_project(project, user):
        """
        Determina se un utente può creare task privati per un progetto.
        Solo il creatore e i collaboratori possono creare task privati.
        """
        if not user or not user.is_authenticated:
            return False
            
        # Il creatore del progetto può sempre creare task
        if project.creator_id == user.id:
            return True
            
        # I collaboratori possono creare task
        from sqlalchemy import and_
        collaborator = db.session.query(Collaborator).filter(
            and_(Collaborator.project_id == project.id,
                 Collaborator.user_id == user.id)
        ).first()
        
        return collaborator is not None

    def __repr__(self):
        return f"<Task {self.title}>"

class Solution(db.Model):
    __tablename__ = 'solution'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False, index=True)
    submitted_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    solution_content = db.Column(db.Text, nullable=False)
    pull_request_url = db.Column(db.String(512), nullable=True) # --- CAMPO PR URL PER FLUSSO SOFTWARE ---
    file_path = db.Column(db.String(2048), nullable=True)
    
    # ⭐ NUOVO: Tipo di contenuto della soluzione
    content_type = db.Column(db.String(20), nullable=True, default='software', index=True)
    # Valori possibili: 'software', 'hardware', 'design', 'documentation', 'media', 'mixed'
    
    # 🔧 GitHub PR Tracking (per ZIP → Auto-PR workflow)
    github_pr_number = db.Column(db.Integer, nullable=True, index=True)
    github_branch = db.Column(db.String(255), nullable=True)
    github_pr_status = db.Column(db.String(50), nullable=True, default='open')  # 'open', 'closed', 'merged'
    github_commit_sha = db.Column(db.String(255), nullable=True)
    
    # 📊 Contribution Analytics
    contribution_category = db.Column(db.String(50), nullable=True, index=True)  # 'code', 'design', 'documentation', etc.
    files_modified = db.Column(db.Integer, nullable=True, default=0)
    files_added = db.Column(db.Integer, nullable=True, default=0)
    lines_added = db.Column(db.Integer, nullable=True, default=0)
    lines_deleted = db.Column(db.Integer, nullable=True, default=0)
    
    is_approved = db.Column(db.Boolean, default=False)
    ai_coherence_score = db.Column(db.Float)
    ai_completeness_score = db.Column(db.Float)
    ai_analysis_timestamp = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    task = db.relationship('Task', back_populates='solutions')
    submitter = db.relationship('User', back_populates='solutions')
    activities = db.relationship('Activity', back_populates='solution', lazy='dynamic', cascade='all, delete-orphan')
    votes = db.relationship('Vote', back_populates='solution', lazy='dynamic', cascade='all, delete-orphan')
    files = db.relationship('SolutionFile', back_populates='solution', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Solution {self.id}>"

# --- MODELLO PER FILE MULTIPLI NELLE SOLUZIONI HARDWARE ---
class SolutionFile(db.Model):
    __tablename__ = 'solution_file'
    id = db.Column(db.Integer, primary_key=True)
    solution_id = db.Column(db.Integer, db.ForeignKey('solution.id'), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(2048), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # 'source', 'prototype', 'documentation', 'visual'
    
    # ⭐ NUOVO: Tipo di contenuto del file
    content_type = db.Column(db.String(20), nullable=True, default='software', index=True)
    # Valori: 'software', 'hardware', 'design', 'documentation', 'media'
    
    # ⭐ NUOVO: Categoria specifica (es: 'logo', 'mockup', 'video', 'audio')
    content_category = db.Column(db.String(50), nullable=True)
    
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(128), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    solution = db.relationship('Solution', back_populates='files')

    def __repr__(self):
        return f"<SolutionFile {self.original_filename}>"

class Vote(db.Model):
    __tablename__ = 'vote'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False, index=True)
    solution_id = db.Column(db.Integer, db.ForeignKey('solution.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = db.relationship('User', back_populates='votes')
    task = db.relationship('Task', back_populates='votes')
    solution = db.relationship('Solution', back_populates='votes')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'task_id', name='uq_user_task_vote'),)

    def __repr__(self):
        return f"<Vote by User {self.user_id} for Solution {self.solution_id}>"

class Collaborator(db.Model):
    __tablename__ = 'collaborator'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    equity_share = db.Column(db.Float, default=0.0)
    role = db.Column(db.String(50), nullable=False, default='collaborator')
    
    project = db.relationship('Project', back_populates='collaborators')
    user = db.relationship('User', back_populates='collaborations')
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='uq_project_user'),)

    def __repr__(self):
        return f"<Collaborator {self.user.username} on Project {self.project.name}>"

class Activity(db.Model):
    __tablename__ = 'activity'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True, index=True)
    solution_id = db.Column(db.Integer, db.ForeignKey('solution.id'), nullable=True, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = db.relationship('User', back_populates='activities')
    project = db.relationship('Project', back_populates='activities')
    task = db.relationship('Task', back_populates='activities')
    solution = db.relationship('Solution', back_populates='activities')

    def __repr__(self):
        return f"<Activity {self.action} by User {self.user_id}>"

class TrainingData(db.Model):
    __tablename__ = 'training_data'
    id = db.Column(db.Integer, primary_key=True)
    source_project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    source_task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    source_solution_id = db.Column(db.Integer, db.ForeignKey('solution.id'), nullable=True)
    input_data = db.Column(db.JSON, nullable=False)
    output_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<TrainingData {self.id}>"

class Endorsement(db.Model):
    __tablename__ = 'endorsement'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'project_id', name='uq_user_project_endorsement'),)

    user = db.relationship('User', back_populates='endorsements')
    project = db.relationship('Project', back_populates='endorsements')

    def __repr__(self):
        return f"<Endorsement by User {self.user_id} for Project {self.project_id}>"

class ProjectInvite(db.Model):
    __tablename__ = 'project_invite'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    inviter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    invitee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    invite_token = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'accepted', 'declined', 'expired'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    project = db.relationship('Project', backref='invites')
    inviter = db.relationship('User', foreign_keys=[inviter_id], backref='sent_invites')
    invitee = db.relationship('User', foreign_keys=[invitee_id], backref='received_invites')

    def __repr__(self):
        return f"<ProjectInvite {self.id} for Project {self.project_id}>"

# --- NUOVI MODELLI PER LE FUNZIONALITÀ STRATEGICHE ---

class WikiPage(db.Model):
    """Modello per le pagine Wiki di ogni progetto con supporto per cartelle"""
    __tablename__ = 'wiki_page'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False, index=True)  # URL-friendly version of title
    content = db.Column(db.Text, nullable=False, default='')  # Stringa vuota per cartelle (SQLite compatibility)
    is_folder = db.Column(db.Boolean, default=False, nullable=False, index=True)  # True se è una cartella
    parent_id = db.Column(db.Integer, db.ForeignKey('wiki_page.id'), nullable=True, index=True)  # ID della cartella padre
    display_order = db.Column(db.Integer, default=0, nullable=False)  # Ordine di visualizzazione
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    project = db.relationship('Project', backref='wiki_pages')
    creator = db.relationship('User', backref='created_wiki_pages')
    parent = db.relationship('WikiPage', remote_side=[id], backref='children')
    revisions = db.relationship('WikiRevision', back_populates='page', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('project_id', 'slug', name='uq_project_wiki_slug'),)

    def __repr__(self):
        folder_marker = "[FOLDER]" if self.is_folder else ""
        return f"<WikiPage {folder_marker} {self.title} in Project {self.project_id}>"
    
    def get_path(self):
        """Restituisce il percorso completo della pagina/cartella come lista di ID"""
        path = []
        current = self
        while current:
            path.insert(0, current.id)
            current = current.parent
        return path
    
    def get_full_path_string(self):
        """Restituisce il percorso completo come stringa (es. "Cartella1 / Cartella2 / Pagina")"""
        path = []
        current = self
        while current:
            path.insert(0, current.title)
            current = current.parent
        return " / ".join(path)
    
    def get_children(self):
        """Restituisce i figli di questa pagina/cartella ordinati"""
        return WikiPage.query.filter_by(
            project_id=self.project_id,
            parent_id=self.id
        ).order_by(WikiPage.is_folder.desc(), WikiPage.display_order, WikiPage.title).all()
    
    def can_delete(self):
        """Verifica se la cartella può essere eliminata (non deve avere figli)"""
        if self.is_folder:
            children_count = WikiPage.query.filter_by(parent_id=self.id).count()
            return children_count == 0
        return True
    
    @staticmethod
    def get_root_pages(project_id):
        """Restituisce tutte le pagine/cartelle root di un progetto"""
        return WikiPage.query.filter_by(
            project_id=project_id,
            parent_id=None
        ).order_by(WikiPage.is_folder.desc(), WikiPage.display_order, WikiPage.title).all()
    
    @staticmethod
    def get_tree_structure(project_id):
        """Restituisce la struttura ad albero completa del wiki del progetto"""
        def build_tree(parent_id=None):
            items = WikiPage.query.filter_by(
                project_id=project_id,
                parent_id=parent_id
            ).order_by(WikiPage.is_folder.desc(), WikiPage.display_order, WikiPage.title).all()
            
            result = []
            for item in items:
                node = {
                    'id': item.id,
                    'title': item.title,
                    'slug': item.slug,
                    'is_folder': item.is_folder,
                    'content': item.content if not item.is_folder else '',  # Stringa vuota per cartelle
                    'created_at': item.created_at,
                    'updated_at': item.updated_at,
                    'creator': item.creator.username,
                    'path': item.get_full_path_string(),
                    'children': build_tree(item.id) if item.is_folder else []
                }
                result.append(node)
            return result
        
        return build_tree()

class WikiRevision(db.Model):
    """Modello per la cronologia delle modifiche delle pagine Wiki"""
    __tablename__ = 'wiki_revision'
    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey('wiki_page.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    edited_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    edit_summary = db.Column(db.String(500), nullable=True)  # Breve descrizione delle modifiche
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    page = db.relationship('WikiPage', back_populates='revisions')
    editor = db.relationship('User', backref='wiki_edits')

    def __repr__(self):
        return f"<WikiRevision {self.id} for Page {self.page_id}>"


# --- MODELLI PER IL SISTEMA DI INVESTIMENTI ---

class ProjectVote(db.Model):
    """Modello per i voti mensili della community sui progetti"""
    __tablename__ = 'project_vote'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    vote_month = db.Column(db.Integer, nullable=False)  # Mese del voto (formato YYYYMM)
    vote_year = db.Column(db.Integer, nullable=False)   # Anno del voto
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    project = db.relationship('Project', backref='community_votes')
    user = db.relationship('User', backref='project_votes')
    
    # Un utente può votare un progetto solo una volta al mese
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', 'vote_month', 'vote_year', name='uq_user_project_monthly_vote'),)

    def __repr__(self):
        return f"<ProjectVote User {self.user_id} -> Project {self.project_id} ({self.vote_year}-{self.vote_month:02d})>"


class InvestmentProject(db.Model):
    """Modello per i progetti pubblicati sulla pagina investimenti"""
    __tablename__ = 'investment_project'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    publication_month = db.Column(db.Integer, nullable=False)  # Mese di pubblicazione (formato YYYYMM)
    publication_year = db.Column(db.Integer, nullable=False)   # Anno di pubblicazione
    total_votes = db.Column(db.Integer, default=0)  # Voti totali ricevuti nel mese
    available_equity_percentage = db.Column(db.Float, default=10.0)  # % di equity disponibile per gli investitori
    equity_price_per_percent = db.Column(db.Float, default=100.0)  # Prezzo per 1% di equity (in €)
    is_active = db.Column(db.Boolean, default=True)  # Se il progetto è ancora attivo per investimenti
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    project = db.relationship('Project', backref='investment_listings')
    investments = db.relationship('Investment', back_populates='investment_project', lazy='dynamic', cascade='all, delete-orphan')
    
    # Un progetto può essere pubblicato solo una volta al mese
    __table_args__ = (db.UniqueConstraint('project_id', 'publication_month', 'publication_year', name='uq_project_monthly_listing'),)

    def __repr__(self):
        return f"<InvestmentProject {self.project.name} ({self.publication_year}-{self.publication_month:02d})>"


class Investment(db.Model):
    """Modello per gli investimenti effettuati dagli utenti"""
    __tablename__ = 'investment'
    id = db.Column(db.Integer, primary_key=True)
    investment_project_id = db.Column(db.Integer, db.ForeignKey('investment_project.id'), nullable=False, index=True)
    investor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    equity_percentage = db.Column(db.Float, nullable=False)  # Percentuale di equity acquistata
    amount_paid = db.Column(db.Float, default=0.0)  # Importo pagato (0 per contributi gratuiti)
    is_free_contribution = db.Column(db.Boolean, default=False)  # Se è un contributo gratuito
    investment_type = db.Column(db.String(20), default='paid')  # 'paid' o 'free'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    investment_project = db.relationship('InvestmentProject', back_populates='investments')
    investor = db.relationship('User', backref='investments')

    def __repr__(self):
        return f"<Investment {self.equity_percentage}% by User {self.investor_id} in Project {self.investment_project.project.name}>"


class EquityConfiguration(db.Model):
    """Modello per la configurazione dell'equity dei progetti"""
    __tablename__ = 'equity_configuration'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    kickthisuss_percentage = db.Column(db.Float, default=1.0)  # % fisso per KickthisUSs (sempre 1%)
    investors_percentage = db.Column(db.Float, default=10.0)   # % destinabile agli investitori
    team_percentage = db.Column(db.Float, default=89.0)       # % rimanente per il team
    last_updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    project = db.relationship('Project', backref='equity_config', uselist=False)
    updated_by_user = db.relationship('User', backref='equity_updates')

    def __repr__(self):
        return f"<EquityConfig Project {self.project_id}: Team {self.team_percentage}%, Investors {self.investors_percentage}%, KickthisUSs {self.kickthisuss_percentage}%>"


# ============================================
# REVENUE TRACKING (Transparency System)
# ============================================
class ProjectRevenue(db.Model):
    """
    Track revenue generated by projects for transparency.
    Public data visible to everyone.
    """
    __tablename__ = 'project_revenue'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    
    # Revenue details
    amount = db.Column(db.Numeric(20, 2), nullable=False)  # Revenue amount
    currency = db.Column(db.String(3), default='EUR', nullable=False)
    source = db.Column(db.String(100))  # 'sale', 'investment', 'subscription', 'donation', etc.
    description = db.Column(db.Text)  # Optional description
    
    # Metadata
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    recorded_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Who recorded it
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('revenue_records', lazy='dynamic', order_by='ProjectRevenue.recorded_at.desc()'))
    recorded_by = db.relationship('User', foreign_keys=[recorded_by_user_id])
    
    def __repr__(self):
        return f'<ProjectRevenue Project {self.project_id}: {self.amount} {self.currency} from {self.source}>'


class RevenueDistribution(db.Model):
    """
    Track distributions made to share holders.
    Public data for transparency and verification.
    """
    __tablename__ = 'revenue_distribution'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Distribution details
    shares_count = db.Column(db.Numeric(20, 6), nullable=False)  # Shares that received distribution
    percentage = db.Column(db.Float, nullable=False)  # Percentage of total shares
    amount = db.Column(db.Numeric(20, 2), nullable=False)  # Amount distributed
    currency = db.Column(db.String(3), default='EUR', nullable=False)
    
    # Source revenue (which revenue record this distribution is from)
    revenue_id = db.Column(db.Integer, db.ForeignKey('project_revenue.id'), nullable=True)
    
    # Blockchain verification (optional)
    transaction_hash = db.Column(db.String(255), nullable=True, index=True)  # Blockchain transaction hash
    blockchain_network = db.Column(db.String(50), nullable=True)  # 'ethereum', 'polygon', etc.
    verified_at = db.Column(db.DateTime, nullable=True)  # When verified on blockchain
    
    # Metadata
    distributed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    distributed_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('distributions', lazy='dynamic', order_by='RevenueDistribution.distributed_at.desc()'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('revenue_distributions', lazy='dynamic'))
    revenue = db.relationship('ProjectRevenue', foreign_keys=[revenue_id])
    distributed_by = db.relationship('User', foreign_keys=[distributed_by_user_id])
    
    def __repr__(self):
        return f'<RevenueDistribution User {self.user_id}: {self.amount} {self.currency} ({self.percentage}%)>'


class TransparencyReport(db.Model):
    """
    Store generated monthly transparency reports.
    Public reports accessible to everyone.
    """
    __tablename__ = 'transparency_report'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    
    # Report period
    report_month = db.Column(db.Integer, nullable=False)  # 1-12
    report_year = db.Column(db.Integer, nullable=False, index=True)
    
    # Report data (JSON)
    report_data = db.Column(db.Text, nullable=False)  # JSON with all report data
    
    # Summary stats (for quick access)
    total_revenue = db.Column(db.Numeric(20, 2), default=0)
    total_distributions = db.Column(db.Numeric(20, 2), default=0)
    new_holders_count = db.Column(db.Integer, default=0)
    
    # Metadata
    generated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    generated_by_system = db.Column(db.Boolean, default=True)  # True if auto-generated
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('transparency_reports', lazy='dynamic', order_by='TransparencyReport.report_year.desc(), TransparencyReport.report_month.desc()'))
    
    # Unique constraint: one report per project per month
    __table_args__ = (
        db.UniqueConstraint('project_id', 'report_month', 'report_year', name='_project_month_year_report_uc'),
    )
    
    def __repr__(self):
        return f'<TransparencyReport Project {self.project_id}: {self.report_year}-{self.report_month:02d}>'


# ============================================
# PROPOSTE LIBERE (FREE PROPOSALS)
# ============================================

# Tabella di associazione per task aggregati in una proposta
proposal_tasks = db.Table('proposal_tasks',
    db.Column('proposal_id', db.Integer, db.ForeignKey('free_proposals.id', ondelete='CASCADE'), primary_key=True),
    db.Column('task_id', db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), primary_key=True)
)


class FreeProposal(db.Model):
    """
    Proposta libera che può:
    1. Aggregare più task esistenti
    2. Proporre un nuovo task non ancora definito
    
    Lo sviluppatore specifica l'equity richiesta e la soluzione verrà
    gestita tramite GitHub come le soluzioni normali.
    """
    __tablename__ = 'free_proposals'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id', ondelete='CASCADE'), nullable=False, index=True)
    developer_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Dettagli proposta
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Equity richiesta
    equity_requested = db.Column(db.Float, nullable=False)
    
    # Tipo di proposta
    proposal_type = db.Column(db.String(50), nullable=False, index=True)  # 'multi_task' o 'new_task'

    # Tipologia di contenuto e metodo di pubblicazione (allineato al flusso soluzioni)
    content_type = db.Column(db.String(20), nullable=False, default='software', index=True)
    publish_method = db.Column(db.String(20), nullable=False, default='manual')
    implementation_details = db.Column(db.Text)
    primary_file_path = db.Column(db.String(2048))
    
    # Task esistenti aggregati (many-to-many) - solo se proposal_type = 'multi_task'
    aggregated_tasks = db.relationship('Task', 
                                      secondary=proposal_tasks,
                                      backref=db.backref('proposals', lazy='dynamic'))
    
    # Dettagli se è un nuovo task proposto - solo se proposal_type = 'new_task'
    new_task_details = db.Column(db.Text)
    
    # Status della proposta
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)  # pending, accepted, rejected
    
    # Motivazione della decisione
    decision_note = db.Column(db.Text)
    decided_at = db.Column(db.DateTime)
    
    # --- GITHUB INTEGRATION (come le soluzioni normali) ---
    github_branch_name = db.Column(db.String(200), nullable=True)
    github_pr_url = db.Column(db.String(500), nullable=True)
    github_pr_number = db.Column(db.Integer, nullable=True)
    github_commit_sha = db.Column(db.String(40), nullable=True)
    github_synced_at = db.Column(db.DateTime, nullable=True)
    
    # Privacy
    is_public = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('free_proposals', lazy='dynamic', cascade='all, delete-orphan'))
    developer = db.relationship('User', backref=db.backref('submitted_proposals', lazy='dynamic'))
    files = db.relationship('FreeProposalFile', back_populates='proposal', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<FreeProposal {self.title} by User {self.developer_id} for Project {self.project_id}>'
    
    @property
    def is_pending(self):
        """Verifica se la proposta è in attesa di decisione"""
        return self.status == 'pending'
    
    @property
    def is_accepted(self):
        """Verifica se la proposta è stata accettata"""
        return self.status == 'accepted'
    
    @property
    def is_rejected(self):
        """Verifica se la proposta è stata rifiutata"""
        return self.status == 'rejected'
    
    @property
    def aggregated_task_count(self):
        """Conta i task aggregati"""
        return len(self.aggregated_tasks)
    
    @property
    def total_aggregated_equity(self):
        """Calcola l'equity totale dei task aggregati"""
        if self.proposal_type != 'multi_task':
            return 0.0
        return sum(task.equity_reward or 0.0 for task in self.aggregated_tasks)
    
    @property
    def proposal_type_display(self):
        """Restituisce il tipo di proposta in formato leggibile"""
        return {
            'multi_task': '📦 Aggregazione Task',
            'new_task': '✨ Nuovo Task Proposto'
        }.get(self.proposal_type, self.proposal_type)
    
    @property
    def status_badge_class(self):
        """Restituisce la classe CSS per il badge di status"""
        return {
            'pending': 'warning',
            'accepted': 'success',
            'rejected': 'danger'
        }.get(self.status, 'secondary')
    
    @property
    def status_display(self):
        """Restituisce lo status in formato leggibile"""
        return {
            'pending': '⏳ In Attesa',
            'accepted': '✅ Accettata',
            'rejected': '❌ Rifiutata'
        }.get(self.status, self.status)


class FreeProposalFile(db.Model):
    """File allegati a una proposta libera (parità funzionale con SolutionFile)."""
    __tablename__ = 'free_proposal_file'

    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('free_proposals.id', ondelete='CASCADE'), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(2048), nullable=False)
    file_type = db.Column(db.String(50), nullable=True)
    content_type = db.Column(db.String(20), nullable=True)
    content_category = db.Column(db.String(50), nullable=True)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(128), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    proposal = db.relationship('FreeProposal', back_populates='files')

    def __repr__(self):
        return f"<FreeProposalFile {self.original_filename}>"


# ============================================
# MILESTONE MODEL
# ============================================
class Milestone(db.Model):
    """Modello per le milestone/roadmap di un progetto"""
    __tablename__ = 'milestone'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_date = db.Column(db.Date, nullable=True)  # Data target per il completamento
    completed = db.Column(db.Boolean, default=False, nullable=False, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)  # Data effettiva di completamento
    completed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Chi ha completato
    display_order = db.Column(db.Integer, default=0, nullable=False)  # Ordine di visualizzazione
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    project = db.relationship('Project', backref=db.backref('milestones', lazy='dynamic', cascade='all, delete-orphan', order_by='Milestone.display_order'))
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_milestones')
    completer = db.relationship('User', foreign_keys=[completed_by], backref='completed_milestones')
    
    def __repr__(self):
        status = "✓" if self.completed else "○"
        return f"<Milestone {status} {self.title} in Project {self.project_id}>"
    
    def mark_completed(self, user_id: int):
        """Marca la milestone come completata"""
        self.completed = True
        self.completed_at = datetime.now(timezone.utc)
        self.completed_by = user_id
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_incomplete(self):
        """Marca la milestone come non completata"""
        self.completed = False
        self.completed_at = None
        self.completed_by = None
        self.updated_at = datetime.now(timezone.utc)
    
    @property
    def is_overdue(self):
        """Verifica se la milestone è in ritardo"""
        if not self.target_date or self.completed:
            return False
        from datetime import date
        return date.today() > self.target_date
    
    @property
    def days_until_target(self):
        """Restituisce i giorni rimanenti fino alla data target"""
        if not self.target_date or self.completed:
            return None
        from datetime import date
        delta = self.target_date - date.today()
        return delta.days

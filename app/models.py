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

    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)

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

class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    pitch = db.Column(db.String(500))
    description = db.Column(db.Text)
    rewritten_pitch = db.Column(db.Text)
    cover_image_url = db.Column(db.String(2048))
    repository_url = db.Column(db.String(255), nullable=True) # --- NUOVO CAMPO ---
    github_url = db.Column(db.String(255), nullable=True) # --- CAMPO GITHUB PER FLUSSO SOFTWARE ---
    
    # AI-Generated Project Guide
    ai_mvp_guide = db.Column(db.Text, nullable=True)  # Guida step-by-step per MVP
    ai_feasibility_analysis = db.Column(db.Text, nullable=True)  # Analisi realistica possibilità
    ai_guide_generated_at = db.Column(db.DateTime, nullable=True)  # Timestamp generazione AI
    
    # --- NUOVO: SUPPORTO RICERCHE SCIENTIFICHE ---
    project_type = db.Column(db.String(20), nullable=False, default='commercial', index=True)  # 'commercial' o 'scientific'
    
    category = db.Column(db.String(50), nullable=False, index=True)
    creator_equity = db.Column(db.Float, nullable=True, default=5.0)  # Ora nullable per ricerche scientifiche
    platform_fee = db.Column(db.Float, nullable=False, default=1.0)
    status = db.Column(db.String(50), nullable=False, default='open', index=True)
    endorsement_count = db.Column(db.Integer, default=0, nullable=False)
    private = db.Column(db.Boolean, default=False, nullable=False)  # --- NUOVO CAMPO per progetti privati ---
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    creator = db.relationship('User', back_populates='projects')
    tasks = db.relationship('Task', back_populates='project', lazy='dynamic', cascade='all, delete-orphan', foreign_keys='Task.project_id')
    collaborators = db.relationship('Collaborator', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('Activity', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')
    endorsements = db.relationship('Endorsement', back_populates='project', lazy='dynamic', cascade='all, delete-orphan')

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

    def __repr__(self):
        return f"<Project {self.name} ({self.project_type})>"

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
    phase = db.Column(db.String(50))
    difficulty = db.Column(db.String(50))
    is_suggestion = db.Column(db.Boolean, default=False)
    is_private = db.Column(db.Boolean, default=False)  # Nuovo campo per task privati
    
    # Campi specifici per esperimenti di validazione
    hypothesis = db.Column(db.Text, nullable=True)  # Ipotesi da testare
    test_method = db.Column(db.Text, nullable=True)  # Metodo di test
    results = db.Column(db.Text, nullable=True)  # Risultati del test
    
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
    """Modello per le pagine Wiki di ogni progetto"""
    __tablename__ = 'wiki_page'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False, index=True)  # URL-friendly version of title
    content = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    project = db.relationship('Project', backref='wiki_pages')
    creator = db.relationship('User', backref='created_wiki_pages')
    revisions = db.relationship('WikiRevision', back_populates='page', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('project_id', 'slug', name='uq_project_wiki_slug'),)

    def __repr__(self):
        return f"<WikiPage {self.title} in Project {self.project_id}>"

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

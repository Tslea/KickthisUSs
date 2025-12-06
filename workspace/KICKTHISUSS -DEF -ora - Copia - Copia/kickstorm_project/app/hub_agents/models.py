from app.extensions import db
from datetime import datetime

class HubProject(db.Model):
    """
    Gestisce lo stato 'Dual Mode' e il contesto AI per ogni progetto.
    Sostituisce la logica del vecchio MVP/Wiki.
    """
    __tablename__ = 'hub_projects'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False) # Assumo esista una tabella 'project'
    
    # Mode: 'wiki' (normale) o 'ai_hub' (agenti attivi)
    mode = db.Column(db.String(20), default='wiki') 
    
    # Riferimento al namespace del Vector DB (Pinecone/Chroma)
    vector_namespace = db.Column(db.String(100))
    
    # Punteggi calcolati dall'AI
    readiness_score = db.Column(db.Integer, default=0)
    phase_scores = db.Column(db.JSON)  # Es: {'00_IDEA_VALIDATION': 82, ...}
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relazioni
    documents = db.relationship('HubDocument', backref='hub_project', lazy=True)
    conversations = db.relationship('AIConversation', backref='hub_project', lazy=True)
    context_entries = db.relationship('ProjectContext', backref='hub_project', lazy='dynamic')


class ProjectContext(db.Model):
    """
    Stores progressive context summaries for AI-generated content.
    Uses DeepSeek for cost-effective summarization.
    Each file gets summarized when saved, building a growing project context.
    """
    __tablename__ = 'project_contexts'
    
    id = db.Column(db.Integer, primary_key=True)
    hub_project_id = db.Column(db.Integer, db.ForeignKey('hub_projects.id'), nullable=False)
    
    # Tipo di contesto: 'file_summary', 'global_context', 'task_context'
    context_type = db.Column(db.String(50), nullable=False, default='file_summary')
    
    # Riferimento al documento (per file_summary)
    document_id = db.Column(db.Integer, db.ForeignKey('hub_documents.id'), nullable=True)
    document_filename = db.Column(db.String(255), nullable=True)
    document_category = db.Column(db.String(100), nullable=True)
    
    # Il riassunto/contesto generato da DeepSeek
    summary = db.Column(db.Text, nullable=False)
    
    # Token count stimato per gestire la lunghezza
    token_count = db.Column(db.Integer, default=0)
    
    # Versione del documento quando è stato creato il summary
    source_version = db.Column(db.Integer, default=1)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Index per ricerche veloci
    __table_args__ = (
        db.Index('idx_project_context_lookup', 'hub_project_id', 'context_type'),
        db.Index('idx_project_context_document', 'hub_project_id', 'document_id'),
    )
    
    def __repr__(self):
        return f'<ProjectContext {self.id} - {self.context_type} for HubProject {self.hub_project_id}>'

class HubDocument(db.Model):
    """
    Documenti auto-generati o manuali all'interno dell'Hub.
    """
    __tablename__ = 'hub_documents'

    id = db.Column(db.Integer, primary_key=True)
    hub_project_id = db.Column(db.Integer, db.ForeignKey('hub_projects.id'), nullable=False)
    
    # Categoria basata sulla struttura cartelle (es: '01_MARKET_RESEARCH')
    category = db.Column(db.String(100), nullable=False)
    
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text) # Contenuto Markdown
    
    # Metadati AI
    completion_percent = db.Column(db.Integer, default=0)
    ai_generated = db.Column(db.Boolean, default=False)
    embedding_id = db.Column(db.String(100)) # ID nel Vector DB
    version = db.Column(db.Integer, default=1)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    last_ai_review = db.Column(db.DateTime)

class AIConversation(db.Model):
    """
    Storico chat contestuale per il Mentor AI.
    """
    __tablename__ = 'ai_conversations'

    id = db.Column(db.Integer, primary_key=True)
    hub_project_id = db.Column(db.Integer, db.ForeignKey('hub_projects.id'), nullable=False)
    
    # Se la chat è specifica su un documento
    document_id = db.Column(db.Integer, db.ForeignKey('hub_documents.id'), nullable=True)
    
    user_message = db.Column(db.Text)
    ai_response = db.Column(db.Text)
    
    # Quali documenti l'AI ha usato per rispondere (RAG)
    context_docs = db.Column(db.JSON) 
    citations = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ValidationIssue(db.Model):
    """
    Problemi di coerenza rilevati dal Validation Engine.
    """
    __tablename__ = 'validation_issues'

    id = db.Column(db.Integer, primary_key=True)
    hub_project_id = db.Column(db.Integer, db.ForeignKey('hub_projects.id'), nullable=False)
    
    severity = db.Column(db.String(20))  # critical, warning, info
    issue_type = db.Column(db.String(50))  # conflict, missing, incomplete
    
    affected_docs = db.Column(db.JSON) # Lista ID documenti coinvolti
    description = db.Column(db.Text)
    suggestion = db.Column(db.Text)
    
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

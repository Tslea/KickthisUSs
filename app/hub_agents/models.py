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

from flask import render_template, jsonify, request, current_app, make_response
from flask_login import current_user, login_required
from . import hub_agents_bp
from .models import HubProject, HubDocument
from .structure_generator import generate_hub_structure, HUB_STRUCTURE
from .ai_service import get_ai_chat_response, generate_document_content
from .rag_service import rag_service
from app.models import Project
from app.extensions import db
from app.decorators import project_member_required
from app.cache import cache, make_project_structure_key, invalidate_project_cache, make_document_cache_key
import os
import io
import markdown
from xhtml2pdf import pisa
from datetime import datetime

# Import Context Service for progressive context building
try:
    from .context_service import update_document_context, get_context_for_document_generation
    CONTEXT_SERVICE_AVAILABLE = True
except ImportError as e:
    CONTEXT_SERVICE_AVAILABLE = False
    print(f"Context service not available: {e}")

# Import Enhanced RAG Service with fallback
try:
    from .enhanced_rag_service import get_rag_service, EnhancedRAGService
    ENHANCED_RAG_AVAILABLE = True
except ImportError:
    ENHANCED_RAG_AVAILABLE = False

def get_active_rag_service():
    """Get the best available RAG service."""
    if ENHANCED_RAG_AVAILABLE:
        try:
            enhanced = get_rag_service()
            if enhanced.initialize():
                return enhanced
        except Exception as e:
            current_app.logger.warning(f"Enhanced RAG not available: {e}")
    return rag_service

# Trigger reload after installing xhtml2pdf

@hub_agents_bp.route('/dashboard/<int:project_id>')
@login_required
@project_member_required
def dashboard(project_id):
    """
    Main Dashboard HUB AGENTS.
    Sostituisce la vecchia vista MVP/Wiki.
    """
    # Recupera il progetto Hub se esiste
    hub_project = HubProject.query.filter_by(project_id=project_id).first()
    
    # Se non esiste, passiamo None, il template mostrerà il pulsante per attivare
    return render_template('hub_agents/dashboard.html', project_id=project_id, hub_project=hub_project)

@hub_agents_bp.route('/activate/<int:project_id>', methods=['POST'])
@login_required
@project_member_required
def activate_ai_hub(project_id):
    """
    Attiva la modalità AI Hub e genera la struttura cartelle.
    Funziona anche come 'Sync' se la struttura esiste ma il DB non è allineato.
    """
    # 1. Trova il path del progetto
    project_path = os.path.join(current_app.root_path, '..', 'projects_data', str(project_id))
    
    if not os.path.exists(project_path):
        try:
            os.makedirs(project_path)
        except OSError:
            pass

    # 2. Genera struttura su disco (idempotente)
    try:
        generate_hub_structure(project_path, f"Project_{project_id}")
        
        # 3. Gestione DB
        hub_project = HubProject.query.filter_by(project_id=project_id).first()
        if not hub_project:
            new_hub_project = HubProject(
                project_id=project_id,
                mode='ai_hub',
                readiness_score=0
            )
            db.session.add(new_hub_project)
            db.session.commit()
            hub_project = new_hub_project
            
        # 4. Sync Documents (Popola HubDocument basandosi su HUB_STRUCTURE)
        count = 0
        for category, filenames in HUB_STRUCTURE.items():
            for filename in filenames:
                exists = HubDocument.query.filter_by(
                    hub_project_id=hub_project.id, 
                    filename=filename
                ).first()
                
                if not exists:
                    doc = HubDocument(
                        hub_project_id=hub_project.id,
                        category=category,
                        filename=filename,
                        content="", # Will load from disk if empty
                        ai_generated=False
                    )
                    db.session.add(doc)
                    count += 1
        
        if count > 0:
            db.session.commit()
        
        return jsonify({
            "status": "success", 
            "message": f"AI Hub Activated/Synced. {count} documents added.", 
            "files_created": count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@hub_agents_bp.route('/chat/message', methods=['POST'])
@login_required
@project_member_required
def chat_message():
    """
    Endpoint per la chat AI contestuale.
    """
    data = request.json
    user_msg = data.get('message')
    context_doc = data.get('context_doc')
    history = data.get('history', []) # List of {role, content}
    
    # RAG: Retrieve relevant context
    # Assumiamo che project_id sia nella sessione o passato nel body. 
    # Per ora lo prendiamo dal referer o lo aggiungiamo al JS.
    # Ma wait, il JS non manda project_id. Dobbiamo aggiungerlo.
    # Per ora proviamo a estrarlo se possibile, o modifichiamo il JS.
    # Modificherò il JS per inviare project_id.
    project_id = data.get('project_id') 
    
    rag_context = ""
    if project_id:
        active_rag = get_active_rag_service()
        active_rag.initialize()
        rag_context = active_rag.query_context(project_id, user_msg)
    
    # Combine context
    full_context = context_doc
    if rag_context:
        full_context += f"\n\n--- RELEVANT PROJECT DOCUMENTS ---\n{rag_context}"

    # Aggiungi il messaggio corrente alla history
    history.append({"role": "user", "content": user_msg})
    
    response = get_ai_chat_response(history, full_context)
    
    return jsonify({"response": response})

@hub_agents_bp.route('/api/structure/<int:project_id>')
@login_required
@project_member_required
def get_project_structure(project_id):
    """
    Restituisce la struttura dei file per il frontend.
    Combina i documenti presenti nel DB con la struttura di default HUB_STRUCTURE
    in modo da mostrare sempre tutti i file attesi.
    
    Uses caching for improved performance.
    """
    # Try to get from cache first
    cache_key = make_project_structure_key(project_id)
    cached_structure = cache.get(cache_key)
    if cached_structure is not None:
        return jsonify(cached_structure)
    
    hub_project = HubProject.query.filter_by(project_id=project_id).first()
    if not hub_project:
        return jsonify({})

    documents = HubDocument.query.filter_by(hub_project_id=hub_project.id).all()

    # Crea lookup rapido per {categoria: {filename: doc}}
    doc_lookup = {}
    for doc in documents:
        if doc.category not in doc_lookup:
            doc_lookup[doc.category] = {}
        doc_lookup[doc.category][doc.filename] = doc

    structure = {}

    # 1. Aggiungi tutte le categorie/file definiti nella struttura base
    for category, filenames in HUB_STRUCTURE.items():
        structure[category] = []
        for filename in filenames:
            doc = doc_lookup.get(category, {}).get(filename)
            structure[category].append({
                'id': doc.id if doc else None,
                'filename': filename,
                'completion': doc.completion_percent if doc else 0,
                'exists': True if doc else False
            })

    # 2. Aggiungi eventuali documenti custom (categorie o file non in HUB_STRUCTURE)
    for doc in documents:
        if doc.category not in structure:
            structure[doc.category] = []

        if not any(entry['filename'] == doc.filename for entry in structure[doc.category]):
            structure[doc.category].append({
                'id': doc.id,
                'filename': doc.filename,
                'completion': doc.completion_percent,
                'exists': True
            })

    # 3. Ordina le categorie alfabeticamente per stabilità
    sorted_structure = {k: structure[k] for k in sorted(structure)}
    
    # Cache the result for 5 minutes
    cache.set(cache_key, sorted_structure, timeout=300)
    
    return jsonify(sorted_structure)

@hub_agents_bp.route('/api/create_document', methods=['POST'])
@login_required
@project_member_required
def create_document():
    """Crea un nuovo file (e cartella se non esiste)"""
    data = request.json
    project_id = data.get('project_id')
    filename = data.get('filename')
    category = data.get('category') # Questo agisce come nome cartella

    if not filename or not category:
        return jsonify({'status': 'error', 'message': 'Filename and category required'}), 400

    if not filename.endswith('.md'):
        filename += '.md'

    hub_project = HubProject.query.filter_by(project_id=project_id).first()
    if not hub_project:
        return jsonify({'status': 'error', 'message': 'Project not found'}), 404
    
    # Verifica duplicati
    exists = HubDocument.query.filter_by(
        hub_project_id=hub_project.id, 
        category=category, 
        filename=filename
    ).first()
    
    if exists:
        return jsonify({'status': 'error', 'message': 'File already exists'}), 400

    new_doc = HubDocument(
        hub_project_id=hub_project.id,
        category=category,
        filename=filename,
        content=f"# {filename.replace('.md', '').replace('_', ' ').title()}\n\nCreated manually.",
        ai_generated=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.session.add(new_doc)
    db.session.commit()
    
    # Invalidate cache when document is created
    invalidate_project_cache(project_id)
    
    return jsonify({'status': 'success', 'filename': filename, 'id': new_doc.id})

@hub_agents_bp.route('/generate/content', methods=['POST'])
@login_required
@project_member_required
def generate_content():
    """
    Genera contenuto per un documento specifico.
    """
    try:
        data = request.json
        if not data:
            current_app.logger.error("generate_content: request.json is None")
            return jsonify({"error": "Invalid request data", "content": ""}), 400
        
        project_id = data.get('project_id')
        doc_type = data.get('doc_type')
        
        if not project_id:
            current_app.logger.error("generate_content: project_id is missing")
            return jsonify({"error": "Project ID is required", "content": ""}), 400
        
        if not doc_type:
            current_app.logger.error("generate_content: doc_type is missing")
            return jsonify({"error": "Document type is required", "content": ""}), 400
        
        project = Project.query.get(project_id)
        if not project:
            current_app.logger.error(f"generate_content: Project {project_id} not found")
            return jsonify({"error": "Project not found", "content": ""}), 404
            
        # Costruisci project_context con tutte le informazioni disponibili
        # Usa rewritten_pitch se disponibile, altrimenti pitch
        pitch_text = project.rewritten_pitch or project.pitch or ""
        
        project_context = {
            "name": project.name or "",
            "description": project.description or "",
            "pitch": pitch_text,
            "rewritten_pitch": project.rewritten_pitch or "",
            "category": project.category or "",
            "project_type": project.project_type or "commercial",
            "ai_mvp_guide": project.ai_mvp_guide or "",
            "ai_feasibility_analysis": project.ai_feasibility_analysis or ""
        }
        
        # ⭐ NEW: Add progressive context from previously generated documents
        if CONTEXT_SERVICE_AVAILABLE:
            try:
                hub_project = HubProject.query.filter_by(project_id=project_id).first()
                if hub_project:
                    progressive_context = get_context_for_document_generation(hub_project.id, doc_type)
                    if progressive_context:
                        project_context["progressive_context"] = progressive_context
                        current_app.logger.info(f"generate_content: Added progressive context ({len(progressive_context)} chars)")
            except Exception as ctx_error:
                current_app.logger.warning(f"generate_content: Could not get progressive context: {ctx_error}")
        
        current_app.logger.info(f"generate_content: Project context - name={project_context['name']}, category={project_context['category']}, has_pitch={bool(pitch_text)}, has_ai_guide={bool(project_context['ai_mvp_guide'])}")
        
        current_app.logger.info(f"generate_content: Generating content for doc_type={doc_type}, project_id={project_id}")
        content = generate_document_content(doc_type, project_context)
        
        # Assicurati che content non sia None o vuoto
        if not content or content.strip() == "":
            current_app.logger.warning(f"generate_content: Empty content returned for doc_type={doc_type}")
            content = "Errore nella generazione del contenuto. Il servizio AI potrebbe non essere disponibile."
        
        # Log per debug
        content_length = len(content) if content else 0
        current_app.logger.info(f"generate_content: Returning content, length={content_length}, type={type(content)}")
        
        try:
            response = jsonify({"content": content})
            current_app.logger.info(f"generate_content: JSON response created successfully")
            return response
        except Exception as json_error:
            current_app.logger.error(f"generate_content: Error creating JSON response: {json_error}", exc_info=True)
            # Prova a pulire il contenuto da caratteri problematici
            try:
                # Rimuovi caratteri di controllo non validi per JSON
                cleaned_content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\r\t')
                response = jsonify({"content": cleaned_content})
                current_app.logger.info(f"generate_content: JSON response created after cleaning")
                return response
            except Exception as e2:
                current_app.logger.error(f"generate_content: Failed to create JSON even after cleaning: {e2}")
                return jsonify({"error": "Errore nella serializzazione del contenuto", "content": ""}), 500
    
    except Exception as e:
        current_app.logger.error(f"Error in generate_content: {e}", exc_info=True)
        return jsonify({"error": str(e), "content": "Errore nella generazione del contenuto."}), 500

@hub_agents_bp.route('/save/document', methods=['POST'])
@login_required
@project_member_required
def save_document():
    """
    Salva il contenuto di un documento.
    """
    data = request.json
    project_id = data.get('project_id')
    filename = data.get('filename')
    category = data.get('category')  # ⭐ NEW: Get category from request
    content = data.get('content')
    
    current_app.logger.info(f"save_document: project_id={project_id}, filename={filename}, category={category}, content_length={len(content) if content else 0}")
    
    hub_project = HubProject.query.filter_by(project_id=project_id).first()
    if not hub_project:
        current_app.logger.error(f"save_document: Hub Project not found for project_id={project_id}")
        return jsonify({"error": "Hub Project not found"}), 404
        
    # ⭐ FIXED: Search by both filename AND category
    doc = HubDocument.query.filter_by(
        hub_project_id=hub_project.id, 
        filename=filename,
        category=category  # ⭐ NEW: Use category in lookup
    ).first()
    
    if not doc:
        current_app.logger.info(f"save_document: Document not found, creating new: {filename} in {category}")
        # Create new document with correct category
        doc = HubDocument(
            hub_project_id=hub_project.id,
            filename=filename,
            category=category,  # ⭐ FIXED: Use actual category instead of "GENERAL"
            content=content,
            version=1,
            ai_generated=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(doc)
    else:
        current_app.logger.info(f"save_document: Updating existing document id={doc.id}")
        doc.content = content
        doc.version += 1
        doc.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        current_app.logger.info(f"save_document: Successfully saved document id={doc.id}, version={doc.version}")
        
        # Invalidate cache when document is saved
        invalidate_project_cache(project_id)
        
        # ⭐ CRITICAL: Also invalidate the specific document cache with category-aware key
        doc_cache_key = make_document_cache_key(int(project_id), f"{category}_{filename}")
        cache.delete(doc_cache_key)
        # Also try without category for backwards compatibility
        cache.delete(make_document_cache_key(int(project_id), filename))
        current_app.logger.info(f"save_document: Cache invalidated for keys: {doc_cache_key}")
        
        # RAG: Index the document using enhanced service
        try:
            active_rag = get_active_rag_service()
            active_rag.initialize()
            active_rag.upsert_document(project_id, filename, content)
            current_app.logger.info(f"save_document: RAG indexed successfully")
        except Exception as rag_error:
            current_app.logger.warning(f"save_document: RAG indexing failed (non-critical): {rag_error}")
        
        # ⭐ NEW: Update progressive context using DeepSeek
        if CONTEXT_SERVICE_AVAILABLE and content and len(content) > 100:
            try:
                update_document_context(
                    hub_project_id=hub_project.id,
                    document_id=doc.id,
                    filename=filename,
                    category=category,
                    content=content,
                    version=doc.version
                )
                db.session.commit()  # Commit context changes
                current_app.logger.info(f"save_document: Progressive context updated for {filename}")
            except Exception as ctx_error:
                current_app.logger.warning(f"save_document: Context update failed (non-critical): {ctx_error}")
        
        return jsonify({"status": "success", "version": doc.version})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"save_document: Database error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@hub_agents_bp.route('/load/document', methods=['GET'])
@login_required
@project_member_required
def load_document():
    """
    Carica il contenuto di un documento (da DB o Disk).
    Uses caching for improved performance.
    """
    try:
        current_app.logger.info(f"load_document: Request received - args={request.args}")
        
        project_id = request.args.get('project_id')
        filename = request.args.get('filename')
        category = request.args.get('category')  # ⭐ NEW: Get category from request
        
        current_app.logger.info(f"load_document: project_id={project_id}, filename={filename}, category={category}")
        
        if not project_id or not filename:
            current_app.logger.error(f"load_document: Missing parameters")
            return jsonify({"error": "Missing parameters", "content": ""}), 400
        
        # Try cache first - include category in cache key for uniqueness
        cache_key = make_document_cache_key(int(project_id), f"{category}_{filename}" if category else filename)
        cached_content = cache.get(cache_key)
        if cached_content is not None:
            current_app.logger.info(f"load_document: Cache hit for {filename}")
            return jsonify({"content": cached_content, "source": "cache"})
            
        hub_project = HubProject.query.filter_by(project_id=project_id).first()
        if not hub_project:
            current_app.logger.error(f"load_document: Hub Project not found for project_id={project_id}")
            return jsonify({"error": "Hub Project not found", "content": ""}), 404

        # 1. Cerca nel DB (priorità alle modifiche salvate)
        # ⭐ FIXED: Search by both filename AND category for precise matching
        if category:
            doc = HubDocument.query.filter_by(hub_project_id=hub_project.id, filename=filename, category=category).first()
        else:
            # Fallback for backwards compatibility
            doc = HubDocument.query.filter_by(hub_project_id=hub_project.id, filename=filename).first()
        
        # ⭐ CRITICAL FIX: Check if document exists, NOT if content is truthy
        # This allows saving empty content (user deletes everything)
        if doc and doc.content is not None:
            current_app.logger.info(f"load_document: Found in DB - filename={filename}, category={doc.category}, content_length={len(doc.content)}")
            # Cache the content with category-aware key
            cache.set(cache_key, doc.content, timeout=300)
            return jsonify({"content": doc.content, "source": "db", "category": doc.category})
            
        # 2. Se non in DB, cerca su disco (template iniziale)
        project_path = os.path.join(current_app.root_path, '..', 'projects_data', str(project_id))
        current_app.logger.info(f"load_document: Searching in disk - path={project_path}")
        
        # TODO: Migliorare la ricerca del file. Per ora proviamo a cercare in tutte le sottocartelle
        file_content = ""
        found = False
        
        for root, dirs, files in os.walk(project_path):
            if filename in files:
                try:
                    with open(os.path.join(root, filename), 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    found = True
                    current_app.logger.info(f"load_document: Found on disk - filename={filename}, content_length={len(file_content)}")
                    break
                except Exception as e:
                    current_app.logger.error(f"load_document: Error reading file {filename}: {e}")
                    return jsonify({"error": f"Error reading file: {str(e)}", "content": ""}), 500
        
        if found:
            # Cache the content from disk
            cache.set(cache_key, file_content, timeout=300)
            return jsonify({"content": file_content, "source": "disk"})
        
        current_app.logger.info(f"load_document: File not found - filename={filename}, returning empty content")
        return jsonify({"content": "", "source": "not_found"})
        
    except Exception as e:
        current_app.logger.error(f"load_document: Unexpected error - {e}", exc_info=True)
        return jsonify({"error": str(e), "content": ""}), 500

@hub_agents_bp.route('/api/delete_document', methods=['POST'])
@login_required
@project_member_required
def delete_document():
    """Elimina un documento"""
    data = request.json
    project_id = data.get('project_id')
    filename = data.get('filename')

    if not project_id or not filename:
        return jsonify({'status': 'error', 'message': 'Missing parameters'}), 400

    hub_project = HubProject.query.filter_by(project_id=project_id).first()
    if not hub_project:
        return jsonify({'status': 'error', 'message': 'Project not found'}), 404

    doc = HubDocument.query.filter_by(hub_project_id=hub_project.id, filename=filename).first()
    if doc:
        db.session.delete(doc)
        db.session.commit()
        
        # Invalidate cache when document is deleted
        invalidate_project_cache(project_id)
        
        return jsonify({'status': 'success', 'message': 'File deleted'})
    
    return jsonify({'status': 'error', 'message': 'File not found'}), 404

@hub_agents_bp.route('/export/pitch-deck/<int:project_id>')
@login_required
@project_member_required
def export_pitch_deck(project_id):
    """
    Genera un PDF Pitch Deck basato sui file Markdown del progetto.
    """
    hub_project = HubProject.query.filter_by(project_id=project_id).first()
    project = Project.query.get_or_404(project_id)
    
    if not hub_project:
        return "Hub Project not active", 404

    def get_doc_html(filename):
        doc = HubDocument.query.filter_by(hub_project_id=hub_project.id, filename=filename).first()
        content = ""
        if doc and doc.content:
            content = doc.content
        else:
            # Fallback to disk if needed, or just empty
            pass
            
        # Convert Markdown to HTML
        if content:
            return markdown.markdown(content)
        return "<p><em>Content not yet generated.</em></p>"

    # Mappa dei file chiave per il Pitch Deck
    slides_content = {
        'problem_html': get_doc_html('problem_definition.md'),
        'solution_html': get_doc_html('solution_hypothesis.md'),
        'market_html': get_doc_html('market_size_analysis.md'),
        'business_html': get_doc_html('business_model_canvas.md'),
        'team_html': get_doc_html('organizational_structure.md')
    }

    # Render HTML Template
    html = render_template(
        'hub_agents/pitch_deck_pdf.html',
        project=project,
        user=current_user,
        date=datetime.now().strftime('%Y-%m-%d'),
        **slides_content
    )

    # Create PDF
    pdf_output = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        io.BytesIO(html.encode("utf-8")),
        dest=pdf_output
    )

    if pisa_status.err:
        return f"PDF generation error: {pisa_status.err}", 500

    response = make_response(pdf_output.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=PitchDeck_{project.name}.pdf'
    
    return response

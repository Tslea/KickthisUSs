"""
Context Service - Progressive Context Building using DeepSeek
Uses DeepSeek for cost-effective summarization of project documents.
Grok then uses this summarized context for generation tasks.
"""

import os
import json
import httpx
from openai import OpenAI
from flask import current_app
from datetime import datetime
from app.extensions import db

# DeepSeek Configuration (separate from main AI service)
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')

# Context limits
MAX_CONTEXT_TOKENS = 4000  # Max tokens for combined context
MAX_SUMMARY_TOKENS = 500   # Max tokens per file summary
MAX_GLOBAL_CONTEXT_TOKENS = 2000  # Max tokens for global context

# Initialize DeepSeek client
deepseek_client = None

def init_deepseek_client():
    """Initialize DeepSeek client for context operations."""
    global deepseek_client
    
    if not DEEPSEEK_API_KEY:
        current_app.logger.warning("DeepSeek API key not found - context service will be limited")
        return None
    
    try:
        deepseek_client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            http_client=httpx.Client(proxies={})
        )
        current_app.logger.info("DeepSeek client initialized for context service")
        return deepseek_client
    except Exception as e:
        current_app.logger.error(f"Failed to initialize DeepSeek client: {e}")
        return None


def get_deepseek_client():
    """Get or initialize DeepSeek client."""
    global deepseek_client
    if deepseek_client is None:
        init_deepseek_client()
    return deepseek_client


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (4 chars ≈ 1 token)."""
    return len(text) // 4


def summarize_document(content: str, filename: str, category: str) -> str:
    """
    Summarize a document using DeepSeek.
    Returns a concise summary focusing on key information.
    """
    client = get_deepseek_client()
    
    if not client:
        # Fallback: return truncated content
        return content[:500] + "..." if len(content) > 500 else content
    
    # Skip very short content
    if len(content) < 100:
        return content
    
    prompt = f"""Riassumi questo documento di progetto in modo conciso ma completo.
Mantieni le informazioni chiave come: obiettivi, metriche, decisioni importanti, specifiche tecniche.
Il riassunto deve essere utile come contesto per generare altri documenti correlati.

DOCUMENTO: {filename}
CATEGORIA: {category}

CONTENUTO:
{content[:6000]}  # Limit input

---
Genera un riassunto strutturato di massimo 300 parole in italiano."""

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=MAX_SUMMARY_TOKENS,
            temperature=0.3  # Low temperature for consistent summaries
        )
        
        summary = response.choices[0].message.content.strip()
        current_app.logger.info(f"Document summarized: {filename} ({len(summary)} chars)")
        return summary
        
    except Exception as e:
        current_app.logger.error(f"Error summarizing document {filename}: {e}")
        # Fallback: return truncated content
        return content[:500] + "..." if len(content) > 500 else content


def update_document_context(hub_project_id: int, document_id: int, filename: str, 
                           category: str, content: str, version: int = 1):
    """
    Update or create context summary for a document.
    Called when a document is saved.
    """
    from .models import ProjectContext, HubDocument
    
    # Check if context already exists for this document
    existing = ProjectContext.query.filter_by(
        hub_project_id=hub_project_id,
        document_id=document_id,
        context_type='file_summary'
    ).first()
    
    # Generate summary using DeepSeek
    summary = summarize_document(content, filename, category)
    token_count = estimate_tokens(summary)
    
    if existing:
        # Update existing context
        existing.summary = summary
        existing.token_count = token_count
        existing.source_version = version
        existing.updated_at = datetime.utcnow()
        current_app.logger.info(f"Updated context for document {filename}")
    else:
        # Create new context entry
        new_context = ProjectContext(
            hub_project_id=hub_project_id,
            context_type='file_summary',
            document_id=document_id,
            document_filename=filename,
            document_category=category,
            summary=summary,
            token_count=token_count,
            source_version=version
        )
        db.session.add(new_context)
        current_app.logger.info(f"Created new context for document {filename}")
    
    # Update global context after document change
    try:
        update_global_context(hub_project_id)
    except Exception as e:
        current_app.logger.warning(f"Failed to update global context: {e}")
    
    return summary


def get_all_file_summaries(hub_project_id: int) -> list:
    """Get all file summaries for a project."""
    from .models import ProjectContext
    
    summaries = ProjectContext.query.filter_by(
        hub_project_id=hub_project_id,
        context_type='file_summary'
    ).order_by(ProjectContext.document_category).all()
    
    return summaries


def build_progressive_context(hub_project_id: int, max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
    """
    Build progressive context from all file summaries.
    Prioritizes important documents and respects token limits.
    """
    from .models import ProjectContext
    
    # Priority order for categories
    category_priority = {
        '00_IDEA_VALIDATION': 1,
        '01_MARKET_RESEARCH': 2,
        '02_BUSINESS_MODEL': 3,
        '03_PRODUCT_STRATEGY': 4,
        '04_GO_TO_MARKET': 5,
        '99_OTHER': 99
    }
    
    # Get all summaries
    summaries = get_all_file_summaries(hub_project_id)
    
    if not summaries:
        return ""
    
    # Sort by category priority
    sorted_summaries = sorted(
        summaries, 
        key=lambda s: category_priority.get(s.document_category, 50)
    )
    
    # Build context respecting token limit
    context_parts = []
    total_tokens = 0
    
    for summary in sorted_summaries:
        if total_tokens + summary.token_count > max_tokens:
            # Try to fit a truncated version
            remaining_tokens = max_tokens - total_tokens
            if remaining_tokens > 100:
                truncated = summary.summary[:remaining_tokens * 4]
                context_parts.append(f"[{summary.document_category}/{summary.document_filename}]\n{truncated}...")
            break
        
        context_parts.append(
            f"[{summary.document_category}/{summary.document_filename}]\n{summary.summary}"
        )
        total_tokens += summary.token_count
    
    full_context = "\n\n---\n\n".join(context_parts)
    
    current_app.logger.info(
        f"Built progressive context for project {hub_project_id}: "
        f"{len(context_parts)} files, ~{total_tokens} tokens"
    )
    
    return full_context


def update_global_context(hub_project_id: int):
    """
    Update the global context summary for the project.
    This is a meta-summary of all file summaries, used for quick reference.
    """
    from .models import ProjectContext
    
    client = get_deepseek_client()
    
    # Get all file summaries
    summaries = get_all_file_summaries(hub_project_id)
    
    if not summaries:
        return None
    
    # Build input for global summary
    summaries_text = "\n\n".join([
        f"**{s.document_filename}** ({s.document_category}):\n{s.summary}"
        for s in summaries
    ])
    
    if not client:
        # Fallback: concatenate first parts of summaries
        global_summary = summaries_text[:MAX_GLOBAL_CONTEXT_TOKENS * 4]
    else:
        prompt = f"""Analizza questi riassunti di documenti di un progetto startup e crea un CONTESTO GLOBALE unificato.
Il contesto globale deve catturare:
1. L'essenza del progetto (cosa fa, per chi, perché)
2. Le decisioni strategiche chiave già prese
3. Le metriche e obiettivi definiti
4. Lo stato attuale di sviluppo
5. I punti critici o aree non ancora definite

RIASSUNTI DEI DOCUMENTI:
{summaries_text[:8000]}

---
Genera un contesto globale strutturato di massimo 500 parole che possa essere usato come base per generare nuovi documenti o task."""

        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_GLOBAL_CONTEXT_TOKENS,
                temperature=0.3
            )
            global_summary = response.choices[0].message.content.strip()
        except Exception as e:
            current_app.logger.error(f"Error generating global context: {e}")
            global_summary = summaries_text[:MAX_GLOBAL_CONTEXT_TOKENS * 4]
    
    # Save or update global context
    existing = ProjectContext.query.filter_by(
        hub_project_id=hub_project_id,
        context_type='global_context'
    ).first()
    
    if existing:
        existing.summary = global_summary
        existing.token_count = estimate_tokens(global_summary)
        existing.updated_at = datetime.utcnow()
    else:
        new_global = ProjectContext(
            hub_project_id=hub_project_id,
            context_type='global_context',
            summary=global_summary,
            token_count=estimate_tokens(global_summary)
        )
        db.session.add(new_global)
    
    current_app.logger.info(f"Updated global context for project {hub_project_id}")
    
    return global_summary


def get_global_context(hub_project_id: int) -> str:
    """Get the global context summary for a project."""
    from .models import ProjectContext
    
    global_ctx = ProjectContext.query.filter_by(
        hub_project_id=hub_project_id,
        context_type='global_context'
    ).first()
    
    if global_ctx:
        return global_ctx.summary
    
    # If no global context exists, try to build one
    return update_global_context(hub_project_id) or ""


def get_context_for_document_generation(hub_project_id: int, doc_type: str) -> str:
    """
    Get optimized context for generating a specific document type.
    Includes global context + relevant file summaries.
    """
    from .models import ProjectContext
    
    # Get global context
    global_ctx = get_global_context(hub_project_id)
    
    # Get progressive context (all file summaries within token limit)
    progressive_ctx = build_progressive_context(hub_project_id, max_tokens=2000)
    
    # Combine contexts
    if global_ctx and progressive_ctx:
        context = f"""=== CONTESTO GLOBALE DEL PROGETTO ===
{global_ctx}

=== DOCUMENTI GIÀ COMPILATI ===
{progressive_ctx}"""
    elif global_ctx:
        context = f"""=== CONTESTO GLOBALE DEL PROGETTO ===
{global_ctx}"""
    elif progressive_ctx:
        context = f"""=== DOCUMENTI GIÀ COMPILATI ===
{progressive_ctx}"""
    else:
        context = ""
    
    return context


def get_context_for_task_generation(project_id: int) -> str:
    """
    Get context for AI task generation.
    Used by the suggest-tasks API to provide richer context.
    Includes project description + Hub Agent documents.
    """
    from .models import HubProject
    from app.models import Project
    
    # Get project info for full description
    project = Project.query.get(project_id)
    project_info = ""
    if project:
        project_info = f"""=== INFO PROGETTO ===
Nome: {project.name}
Categoria: {project.category or 'N/A'}
Tipo: {project.project_type or 'commercial'}
Pitch: {project.rewritten_pitch or project.pitch or 'N/A'}
Descrizione: {project.description or 'N/A'}
"""
    
    # Find hub project
    hub_project = HubProject.query.filter_by(project_id=project_id).first()
    
    if not hub_project:
        return project_info if project_info else ""
    
    # Get global context (most efficient)
    global_ctx = get_global_context(hub_project.id)
    
    # Get key file summaries (limited)
    progressive_ctx = build_progressive_context(hub_project.id, max_tokens=1500)
    
    context_parts = []
    
    if project_info:
        context_parts.append(project_info)
    
    if global_ctx:
        context_parts.append(f"=== CONTESTO GLOBALE HUB AGENTS ===\n{global_ctx}")
    
    if progressive_ctx:
        context_parts.append(f"=== DOCUMENTI COMPLETATI ===\n{progressive_ctx}")
    
    if context_parts:
        context = "\n\n".join(context_parts)
        context += "\n\n---\nUsa questo contesto per generare task più pertinenti e specifici per il progetto."
        return context
    
    return ""


def rebuild_all_contexts(hub_project_id: int):
    """
    Rebuild all context summaries for a project.
    Useful for migration or fixing corrupted contexts.
    """
    from .models import HubDocument, ProjectContext
    
    # Get all documents
    documents = HubDocument.query.filter_by(hub_project_id=hub_project_id).all()
    
    rebuilt_count = 0
    
    for doc in documents:
        if doc.content and len(doc.content) > 50:
            try:
                update_document_context(
                    hub_project_id=hub_project_id,
                    document_id=doc.id,
                    filename=doc.filename,
                    category=doc.category,
                    content=doc.content,
                    version=doc.version
                )
                rebuilt_count += 1
            except Exception as e:
                current_app.logger.error(f"Error rebuilding context for {doc.filename}: {e}")
    
    # Commit all changes
    db.session.commit()
    
    current_app.logger.info(f"Rebuilt {rebuilt_count} contexts for project {hub_project_id}")
    
    return rebuilt_count

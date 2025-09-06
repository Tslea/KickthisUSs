"""
API endpoints per le funzionalità AI della Wiki
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Project, WikiPage, Collaborator
from app.ai_services import analyze_with_ai
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

api_ai_wiki = Blueprint('api_ai_wiki', __name__)

def check_wiki_edit_permission(project_id):
    """Verifica se l'utente può modificare la wiki del progetto"""
    project = Project.query.get_or_404(project_id)
    
    # Creatore ha sempre accesso
    if project.creator_id == current_user.id:
        return True, project
    
    # Verifica se è collaboratore
    collaborator = Collaborator.query.filter_by(
        project_id=project_id,
        user_id=current_user.id
    ).first()
    
    if collaborator:
        return True, project
    
    return False, None

@api_ai_wiki.route('/wiki/<int:project_id>/page/<slug>/reorganize', methods=['POST'])
@login_required
def reorganize_wiki_page(project_id, slug):
    """Riorganizza il contenuto di una pagina wiki con AI"""
    try:
        # Verifica permessi
        has_permission, project = check_wiki_edit_permission(project_id)
        if not has_permission:
            return jsonify({
                'success': False,
                'error': 'Non hai i permessi per modificare questa wiki'
            }), 403
        
        # Trova la pagina wiki
        wiki_page = WikiPage.query.filter_by(
            project_id=project_id,
            slug=slug
        ).first_or_404()
        
        if not wiki_page.content or len(wiki_page.content.strip()) < 50:
            return jsonify({
                'success': False,
                'error': 'Il contenuto della pagina è troppo breve per essere riorganizzato'
            }), 400
        
        # Prompt per riorganizzazione
        prompt = f"""
        TASK: Riorganizza e migliora il seguente contenuto di una pagina wiki del progetto "{project.name}".
        
        CONTENUTO ORIGINALE:
        {wiki_page.content}
        
        ISTRUZIONI:
        1. Mantieni tutte le informazioni importanti
        2. Riorganizza in modo logico e strutturato
        3. Migliora la leggibilità con headers, liste e paragrafi
        4. Correggi eventuali errori grammaticali
        5. Usa un linguaggio chiaro e professionale
        6. Mantieni il formato Markdown
        
        FORMATO RISPOSTA: Restituisci solo il contenuto riorganizzato in Markdown, senza commenti aggiuntivi.
        """
        
        # Chiama AI
        reorganized_content = analyze_with_ai(prompt)
        
        if not reorganized_content:
            return jsonify({
                'success': False,
                'error': 'Errore durante la riorganizzazione con AI'
            }), 500
        
        # Salva come revisione
        from app.models import WikiRevision
        revision = WikiRevision(
            page_id=wiki_page.id,
            content=wiki_page.content,  # Salva versione precedente
            edit_summary=f"Backup prima riorganizzazione AI - {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')}",
            created_by=current_user.id,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(revision)
        
        # Aggiorna pagina con contenuto riorganizzato
        wiki_page.content = reorganized_content
        wiki_page.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Contenuto riorganizzato con successo',
            'reorganized_content': reorganized_content
        })
        
    except Exception as e:
        logger.error(f"Errore riorganizzazione wiki: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Errore interno del server'
        }), 500

@api_ai_wiki.route('/wiki/<int:project_id>/page/<slug>/summarize', methods=['POST'])
@login_required
def summarize_wiki_page(project_id, slug):
    """Genera un riassunto del contenuto di una pagina wiki"""
    try:
        # Verifica permessi
        has_permission, project = check_wiki_edit_permission(project_id)
        if not has_permission:
            return jsonify({
                'success': False,
                'error': 'Non hai i permessi per accedere a questa wiki'
            }), 403
        
        # Trova la pagina wiki
        wiki_page = WikiPage.query.filter_by(
            project_id=project_id,
            slug=slug
        ).first_or_404()
        
        if not wiki_page.content or len(wiki_page.content.strip()) < 100:
            return jsonify({
                'success': False,
                'error': 'Il contenuto della pagina è troppo breve per essere riassunto'
            }), 400
        
        # Prompt per riassunto
        prompt = f"""
        TASK: Crea un riassunto conciso e strutturato del seguente contenuto di una pagina wiki del progetto "{project.name}".
        
        CONTENUTO:
        {wiki_page.content}
        
        ISTRUZIONI:
        1. Estrai i concetti principali e le informazioni più importanti
        2. Organizza in punti chiave numerati
        3. Mantieni un linguaggio chiaro e diretto
        4. Includi solo le informazioni essenziali
        5. Massimo 500 parole
        6. Usa formato Markdown per la strutturazione
        
        FORMATO RISPOSTA: 
        ## Riassunto: [Titolo della pagina]
        
        ### Punti Chiave:
        1. [Primo punto importante]
        2. [Secondo punto importante]
        ...
        
        ### Conclusioni:
        [Breve sintesi finale]
        """
        
        # Chiama AI
        summary = analyze_with_ai(prompt)
        
        if not summary:
            return jsonify({
                'success': False,
                'error': 'Errore durante la generazione del riassunto'
            }), 500
        
        return jsonify({
            'success': True,
            'summary': summary,
            'original_length': len(wiki_page.content),
            'summary_length': len(summary)
        })
        
    except Exception as e:
        logger.error(f"Errore riassunto wiki: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Errore interno del server'
        }), 500

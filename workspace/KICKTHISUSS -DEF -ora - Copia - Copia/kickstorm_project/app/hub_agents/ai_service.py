from app.ai_services import client, CURRENT_MODEL, AI_SERVICE_AVAILABLE
from flask import current_app
import json
from .document_prompts import get_document_prompt, get_default_prompt

# Import Enhanced AI Service with fallback
try:
    from app.services.ai_enhanced_service import get_ai_service, is_ai_available
    ENHANCED_AI_AVAILABLE = True
except ImportError:
    ENHANCED_AI_AVAILABLE = False

def get_ai_chat_response(messages, context_doc=None):
    """
    Gestisce la chat contestuale con l'AI.
    Usa Enhanced AI Service se disponibile, altrimenti fallback.
    
    messages: list of dict [{'role': 'user', 'content': '...'}]
    context_doc: contenuto del documento corrente (opzionale)
    """
    # Try Enhanced AI Service first
    if ENHANCED_AI_AVAILABLE:
        try:
            ai_service = get_ai_service()
            if ai_service.available:
                return ai_service.chat_with_context(messages, context=context_doc)
        except Exception as e:
            current_app.logger.warning(f"Enhanced AI failed, using fallback: {e}")
    
    # Fallback to original implementation
    if not AI_SERVICE_AVAILABLE or not client:
        return "AI Service non disponibile. Verifica la configurazione."

    system_prompt = (
        "Sei un AI Startup Mentor esperto. Il tuo obiettivo è guidare il fondatore "
        "nella creazione di una startup di successo. Sii conciso, pratico e diretto. "
        "Usa un tono professionale ma incoraggiante."
    )
    
    if context_doc:
        system_prompt += f"\n\nCONTESTO DOCUMENTO CORRENTE:\n{context_doc}\n\nRispondi tenendo conto di questo contesto."

    # Costruisci la history completa
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=full_messages,
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        current_app.logger.error(f"AI Chat Error: {e}")
        return "Mi dispiace, si è verificato un errore nel generare la risposta."

def generate_document_content(doc_type, project_context):
    """
    Genera il contenuto per un documento specifico.
    doc_type: es. "mvp_definition.md"
    project_context: dict con info sul progetto (nome, pitch, descrizione, categoria, ecc.)
    """
    if not AI_SERVICE_AVAILABLE or not client:
        current_app.logger.warning("AI Service not available or client is None")
        return "AI Service non disponibile. Verifica la configurazione delle API keys."

    if not CURRENT_MODEL:
        current_app.logger.error("CURRENT_MODEL is None - AI service not properly initialized")
        return "Errore: Modello AI non configurato. Verifica la configurazione."

    # Ottieni il prompt specifico per questo tipo di documento
    specific_prompt = get_document_prompt(doc_type)
    
    if specific_prompt:
        # Usa il prompt specifico e formattalo con il project_context
        # Prepara i parametri base
        pitch_text = project_context.get('pitch', project_context.get('rewritten_pitch', 'N/A'))
        
        format_kwargs = {
            'name': project_context.get('name', 'N/A'),
            'pitch': pitch_text,
            'description': project_context.get('description', 'N/A'),
            'category': project_context.get('category', 'N/A'),
            'project_type': project_context.get('project_type', 'commercial'),
        }
        
        # Aggiungi ai_mvp_guide_context solo se disponibile e per mvp_definition
        if doc_type.endswith('mvp_definition.md') and project_context.get('ai_mvp_guide'):
            # Prendi i primi 500 caratteri della guida MVP per non appesantire il prompt
            ai_guide_preview = project_context.get('ai_mvp_guide', '')[:500]
            format_kwargs['ai_mvp_guide_context'] = f"\n- Guida MVP Precedente: {ai_guide_preview}"
        else:
            format_kwargs['ai_mvp_guide_context'] = ''
        
        try:
            prompt = specific_prompt.format(**format_kwargs)
        except KeyError as e:
            # Se manca qualche placeholder, logga e usa valore di default
            current_app.logger.warning(f"Missing placeholder '{e}' in prompt for {doc_type}, using default value")
            format_kwargs[str(e).strip("'")] = 'N/A'
            prompt = specific_prompt.format(**format_kwargs)
        
        # ⭐ NEW: Add progressive context from previously generated documents
        progressive_context = project_context.get('progressive_context', '')
        if progressive_context:
            prompt = f"""{prompt}

---
⭐ CONTESTO PROGRESSIVO - DOCUMENTI GIÀ COMPLETATI:
{progressive_context}

IMPORTANTE: Usa le informazioni dai documenti già completati per mantenere coerenza e continuità nel progetto. Non ripetere informazioni già presenti, ma costruisci su di esse."""
            current_app.logger.info(f"Added progressive context to prompt for {doc_type}")
        
        current_app.logger.info(f"Using specific prompt for {doc_type}")
    else:
        # Usa il prompt generico di fallback
        prompt = get_default_prompt(doc_type).format(
            doc_type=doc_type,
            name=project_context.get('name', 'N/A'),
            pitch=project_context.get('pitch', project_context.get('rewritten_pitch', 'N/A')),
            description=project_context.get('description', 'N/A'),
            category=project_context.get('category', 'N/A'),
            project_type=project_context.get('project_type', 'commercial')
        )
        current_app.logger.info(f"Using default prompt for {doc_type}")

    try:
        current_app.logger.info(f"Calling AI API with model={CURRENT_MODEL}, doc_type={doc_type}")
        response = client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        
        if not response or not response.choices or len(response.choices) == 0:
            current_app.logger.error("AI API returned empty response")
            return "Errore: Risposta vuota dal servizio AI."
        
        content = response.choices[0].message.content
        if not content or content.strip() == "":
            current_app.logger.warning("AI API returned empty content")
            return "Errore: Contenuto vuoto generato dal servizio AI."
        
        current_app.logger.info(f"Successfully generated content for {doc_type} (length: {len(content)})")
        return content
        
    except Exception as e:
        current_app.logger.error(f"AI Generation Error: {e}", exc_info=True)
        return f"Errore nella generazione del contenuto: {str(e)}"

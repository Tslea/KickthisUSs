# app/utils.py
import re
import humanize
import markdown
from markupsafe import escape, Markup
from datetime import datetime, timezone
from contextlib import contextmanager
from .models import (
    ALLOWED_PROJECT_CATEGORIES,
    ALLOWED_TASK_PHASES,
    ALLOWED_TASK_STATUS,
    ALLOWED_TASK_DIFFICULTIES,
    ALLOWED_TASK_TYPES,
    Task 
)
from .validation_rules import VALIDATION_RULES
from .extensions import db

# Try to import bleach for HTML sanitization, fallback to basic escaping
try:
    import bleach
    BLEACH_AVAILABLE = True
except ImportError:
    BLEACH_AVAILABLE = False

# Allowed HTML tags and attributes for user-generated content
ALLOWED_HTML_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
ALLOWED_HTML_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'code': ['class'],
    'pre': ['class']
}

# Correzione: Sostituiti i newline letterali con le loro sequenze di escape (\n, \r\n, \r)
_nl_re = re.compile(r'(\r\n|\n|\r)')

def calculate_project_equity(project):
    """Calcola l'equity totale distribuita per un progetto."""
    if not project:
        return 0.0
    approved_tasks = project.tasks.filter_by(status='approved').all()
    distributed_equity = sum(task.equity_reward for task in approved_tasks)
    return distributed_equity

def register_helpers(app):
    """Registra funzioni helper e filtri per i template Jinja2."""
    
    @app.context_processor
    def inject_allowed_constants():
        return dict(
            ALLOWED_PROJECT_CATEGORIES=ALLOWED_PROJECT_CATEGORIES,
            ALLOWED_TASK_PHASES=ALLOWED_TASK_PHASES,
            ALLOWED_TASK_STATUS=ALLOWED_TASK_STATUS,
            ALLOWED_TASK_DIFFICULTIES=ALLOWED_TASK_DIFFICULTIES,
            ALLOWED_TASK_TYPES=ALLOWED_TASK_TYPES,
            validation_rules=VALIDATION_RULES
        )

    @app.template_filter('format_datetime')
    def format_datetime_filter(value, format='%d %b %Y, %H:%M'):
        if value is None: return ""
        if isinstance(value, str):
            try: value = datetime.fromisoformat(value)
            except ValueError: return value
        return value.strftime(format)

    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if not s: return ""
        escaped_s = escape(s)
        # Correzione: Sostituito il newline letterale con la sua sequenza di escape
        return Markup(_nl_re.sub('<br>\n', escaped_s))

    @app.template_filter('humanize_datetime')
    def humanize_datetime_filter(dt):
        if dt is None: return ""
        if isinstance(dt, str):
            try: dt = datetime.fromisoformat(dt)
            except ValueError: return dt
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return humanize.naturaltime(now - dt)

    @app.template_filter('truncate_text')
    def truncate_text_filter(text, length=255, suffix='...'):
        """Tronca il testo senza tagliare le parole."""
        if not text or len(text) <= length:
            return text
        # Trova l'ultimo spazio prima della lunghezza massima
        last_space = text.rfind(' ', 0, length)
        if last_space == -1: # Nessuno spazio, taglia forzatamente
            return text[:length] + suffix
        return text[:last_space] + suffix

    @app.template_filter('markdown')
    def markdown_filter(text):
        """Converte testo Markdown in HTML formattato."""
        if not text:
            return ""
        
        # Configura markdown con estensioni per migliore formattazione
        md = markdown.Markdown(extensions=[
            'markdown.extensions.fenced_code',  # Code blocks ```
            'markdown.extensions.tables',       # Tabelle
            'markdown.extensions.nl2br',        # Newlines come <br>
            'markdown.extensions.toc',          # Table of contents
            'markdown.extensions.admonition'    # Note e warning boxes
        ])
        
        # Converte markdown in HTML
        html = md.convert(text)
        
        # Aggiungi classi CSS per styling
        html = html.replace('<h1>', '<h1 class="text-3xl font-bold text-gray-900 mb-6 pb-3 border-b border-gray-200">')
        html = html.replace('<h2>', '<h2 class="text-2xl font-semibold text-gray-800 mb-4 mt-8">')
        html = html.replace('<h3>', '<h3 class="text-xl font-semibold text-gray-700 mb-3 mt-6">')
        html = html.replace('<h4>', '<h4 class="text-lg font-medium text-gray-700 mb-2 mt-4">')
        html = html.replace('<p>', '<p class="text-gray-600 mb-4 leading-relaxed">')
        html = html.replace('<ul>', '<ul class="list-disc pl-6 mb-4 space-y-2">')
        html = html.replace('<ol>', '<ol class="list-decimal pl-6 mb-4 space-y-2">')
        html = html.replace('<li>', '<li class="text-gray-600">')
        html = html.replace('<blockquote>', '<blockquote class="border-l-4 border-blue-500 pl-4 italic text-gray-700 mb-4">')
        html = html.replace('<code>', '<code class="bg-gray-100 px-2 py-1 rounded text-sm font-mono">')
        html = html.replace('<pre>', '<pre class="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto mb-4">')
        html = html.replace('<table>', '<table class="min-w-full border border-gray-300 mb-4">')
        html = html.replace('<th>', '<th class="border border-gray-300 px-4 py-2 bg-gray-100 font-semibold">')
        html = html.replace('<td>', '<td class="border border-gray-300 px-4 py-2">')
        
        # Emoji styling per titoli con emoji
        html = re.sub(r'<h([1-6])([^>]*)>([^<]*)(📋|📊|🎯|⚡|🚀|🛠️|💰|⚠️|✅)', 
                     r'<h\1\2><span class="inline-block mr-3 text-2xl">\4</span>\3', html)
        
        return Markup(html)
    
    print("[INFO] Helper e filtri di utils registrati correttamente.")

def get_pending_invite(project_id, user_id):
    """Funzione di utilità per recuperare un invito pendente per un utente e un progetto specifici."""
    from .models import ProjectInvite
    return ProjectInvite.query.filter_by(
        project_id=project_id,
        invitee_id=user_id,
        status='pending'
    ).first()


def sanitize_html(content, allow_markdown=False):
    """
    Sanitizza HTML user-generated per prevenire XSS attacks.
    
    Args:
        content: Stringa HTML da sanitizzare
        allow_markdown: Se True, permette conversione da Markdown a HTML sicuro
    
    Returns:
        Markup: HTML sanitizzato e sicuro
    """
    if not content:
        return Markup("")
    
    # Se bleach è disponibile, usalo per sanitizzazione completa
    if BLEACH_AVAILABLE:
        # Se è markdown, convertilo prima
        if allow_markdown:
            md = markdown.Markdown(extensions=['markdown.extensions.fenced_code', 'markdown.extensions.tables'])
            content = md.convert(content)
        
        # Sanitizza HTML
        cleaned = bleach.clean(
            content,
            tags=ALLOWED_HTML_TAGS,
            attributes=ALLOWED_HTML_ATTRIBUTES,
            strip=True
        )
        return Markup(cleaned)
    else:
        # Fallback: escape tutto se bleach non è disponibile
        if allow_markdown:
            md = markdown.Markdown(extensions=['markdown.extensions.fenced_code', 'markdown.extensions.tables'])
            content = md.convert(content)
        
        # Escape HTML per sicurezza
        return Markup(escape(content))


def _get_field_label(section: str, field: str, rules: dict | None = None) -> str:
    rules = rules or VALIDATION_RULES.get(section, {}).get(field, {})
    default_label = f"{section}.{field}".replace('_', ' ').title()
    return rules.get('label', default_label)


def clean_plain_text_field(section: str, field: str, value: str | None) -> str:
    """
    Applica le regole di validazione per un campo testuale semplice.
    Restituisce la stringa ripulita o solleva ValueError con messaggio user-friendly.
    """
    rules = VALIDATION_RULES.get(section, {}).get(field, {})
    label = _get_field_label(section, field, rules)
    raw_value = '' if value is None else str(value)
    cleaned = raw_value.strip()
    
    min_length = rules.get('min_length')
    max_length = rules.get('max_length')
    pattern = rules.get('pattern')
    required = rules.get('required', True if min_length else False)
    
    if required and not cleaned:
        raise ValueError(f"{label} è obbligatorio.")
    if cleaned and min_length and len(cleaned) < min_length:
        raise ValueError(f"{label} deve contenere almeno {min_length} caratteri.")
    if cleaned and max_length and len(cleaned) > max_length:
        raise ValueError(f"{label} non può superare {max_length} caratteri.")
    if cleaned and pattern and not re.fullmatch(pattern, cleaned):
        raise ValueError(f"{label} contiene caratteri non ammessi.")
    
    return cleaned


def clean_rich_text_field(section: str, field: str, value: str | None) -> str:
    """
    Applica le regole di validazione a un campo che supporta HTML/Markdown
    e restituisce la stringa sanitizzata pronta per l'archiviazione.
    """
    rules = VALIDATION_RULES.get(section, {}).get(field, {})
    label = _get_field_label(section, field, rules)
    raw_value = '' if value is None else str(value)
    cleaned_input = raw_value.strip()
    
    required = rules.get('required', False)
    max_length = rules.get('max_length')
    allow_markdown = rules.get('allow_markdown', False)
    
    if required and not cleaned_input:
        raise ValueError(f"{label} è obbligatorio.")
    if cleaned_input and max_length and len(cleaned_input) > max_length:
        raise ValueError(f"{label} non può superare {max_length} caratteri.")
    
    if not cleaned_input:
        return ''
    
    return str(sanitize_html(cleaned_input, allow_markdown=allow_markdown))


def validate_no_html(text):
    """
    Valida che una stringa non contenga tag HTML.
    Utile per campi che devono contenere solo testo semplice.
    
    Args:
        text: Stringa da validare
    
    Returns:
        bool: True se non contiene HTML, False altrimenti
    
    Raises:
        ValueError: Se il testo contiene HTML
    """
    if not text:
        return True
    
    # Pattern per rilevare tag HTML
    html_pattern = re.compile(r'<[^>]+>')
    if html_pattern.search(text):
        raise ValueError('Il campo non può contenere tag HTML.')
    return True


@contextmanager
def db_transaction():
    """
    Context manager per gestire transazioni database atomiche.
    Esegue commit automatico se tutto va a buon fine, rollback in caso di eccezioni.
    """
    try:
        yield db.session
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
# app/utils.py
import re
import humanize
import markdown
from markupsafe import escape, Markup
from datetime import datetime, timezone
from .models import (
    ALLOWED_PROJECT_CATEGORIES,
    ALLOWED_TASK_PHASES,
    ALLOWED_TASK_STATUS,
    ALLOWED_TASK_DIFFICULTIES,
    ALLOWED_TASK_TYPES,
    Task 
)

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
            ALLOWED_TASK_TYPES=ALLOWED_TASK_TYPES
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
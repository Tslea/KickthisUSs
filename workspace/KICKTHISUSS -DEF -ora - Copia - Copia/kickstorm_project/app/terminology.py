# app/terminology.py
"""
Centralized Terminology Configuration for KickthisUSs

This module provides a single source of truth for all user-facing terminology.
Terms can be configured via environment variables to easily rebrand/rename concepts.

USAGE IN TEMPLATES:
    {{ term.shares }}           -> "TEMPLE" (or configured name)
    {{ term.shares_plural }}    -> "TEMPLE" 
    {{ term.equity }}           -> "TEMPLE"
    {{ term.portfolio }}        -> "TEMPLE Portfolio"
    
USAGE IN PYTHON:
    from app.terminology import get_terms, t
    terms = get_terms()
    message = f"Hai guadagnato {amount} {terms['shares']}"
    # Or shorthand:
    message = f"Hai guadagnato {amount} {t('shares')}"
"""

import os
from functools import lru_cache

# ============================================
# DEFAULT TERMINOLOGY (can be overridden via .env)
# ============================================

DEFAULT_TERMS = {
    # Primary unit name (was "Shares" / "Equity")
    'shares': 'TEMPLE',
    'shares_lower': 'temple',
    'shares_plural': 'TEMPLE',
    'shares_singular': 'TEMPLE',
    
    # Equity terminology
    'equity': 'TEMPLE',
    'equity_lower': 'temple',
    'equity_plural': 'TEMPLE',
    
    # Phantom shares (legacy)
    'phantom_shares': 'TEMPLE',
    
    # UI Labels
    'portfolio_title': 'TEMPLE Portfolio',
    'distribution_title': 'Distribuzione TEMPLE',
    'available_label': 'TEMPLE Disponibili',
    'earned_label': 'TEMPLE Guadagnati',
    'total_label': 'TEMPLE Totali',
    'holders_label': 'Possessori TEMPLE',
    'reward_label': 'Ricompensa TEMPLE',
    'grant_label': 'Assegnazione TEMPLE',
    
    # Action labels
    'earn_action': 'Guadagna TEMPLE',
    'distribute_action': 'Distribuisci TEMPLE',
    'configure_action': 'Configura TEMPLE',
    
    # Status labels
    'system_active': 'Sistema TEMPLE Attivo',
    'auto_distribution': 'Distribuzione Automatica TEMPLE',
    
    # Descriptions
    'what_is_title': 'Cosa sono i TEMPLE?',
    'what_is_description': 'I TEMPLE sono quote di partecipazione virtuale nel progetto. Rappresentano il tuo contributo e possono tradursi in valore reale quando il progetto ha successo.',
    
    # History/Audit
    'history_title': 'Storico TEMPLE',
    'audit_title': 'Audit TEMPLE',
    'change_label': 'Variazione TEMPLE',
    
    # Percentage suffix
    'percentage_suffix': '%',
    
    # Unit symbol (optional, for display)
    'symbol': '⧫',  # Diamond symbol for TEMPLE
}


@lru_cache(maxsize=1)
def get_terms() -> dict:
    """
    Get all terminology terms, with environment variable overrides.
    
    Environment variables are prefixed with TERM_ and uppercased.
    Example: TERM_SHARES=POINTS would change 'shares' to 'POINTS'
    
    Returns:
        dict: Dictionary of all terminology terms
    """
    terms = DEFAULT_TERMS.copy()
    
    # Override with environment variables
    for key in terms.keys():
        env_key = f"TERM_{key.upper()}"
        env_value = os.environ.get(env_key)
        if env_value:
            terms[key] = env_value
    
    # Also check for main override
    main_term = os.environ.get('MAIN_CURRENCY_TERM')
    if main_term:
        # Override all primary terms with the main term
        terms['shares'] = main_term
        terms['shares_lower'] = main_term.lower()
        terms['shares_plural'] = main_term
        terms['shares_singular'] = main_term
        terms['equity'] = main_term
        terms['equity_lower'] = main_term.lower()
        terms['equity_plural'] = main_term
        terms['phantom_shares'] = main_term
    
    return terms


def t(key: str, default: str = None) -> str:
    """
    Shorthand function to get a single term.
    
    Args:
        key: The terminology key to look up
        default: Default value if key not found
        
    Returns:
        str: The term value
        
    Example:
        message = f"Hai guadagnato {amount} {t('shares')}"
    """
    terms = get_terms()
    return terms.get(key, default or key)


def format_amount(amount: float, term_key: str = 'shares') -> str:
    """
    Format an amount with the appropriate term.
    
    Args:
        amount: The numeric amount
        term_key: Which term to use (default 'shares')
        
    Returns:
        str: Formatted string like "10 TEMPLE" or "5.5 TEMPLE"
        
    Example:
        format_amount(10, 'shares')  # "10 TEMPLE"
        format_amount(5.5, 'equity')  # "5.5 TEMPLE"
    """
    terms = get_terms()
    term = terms.get(term_key, 'TEMPLE')
    
    # Format number nicely
    if amount == int(amount):
        return f"{int(amount)} {term}"
    else:
        return f"{amount:.1f} {term}"


def format_percentage(percentage: float) -> str:
    """
    Format a percentage for display.
    
    Args:
        percentage: The percentage value
        
    Returns:
        str: Formatted string like "10%" or "5.5%"
    """
    if percentage == int(percentage):
        return f"{int(percentage)}%"
    else:
        return f"{percentage:.1f}%"


# ============================================
# TEMPLATE CONTEXT PROCESSOR
# ============================================

def inject_terminology():
    """
    Flask context processor to inject terminology into all templates.
    
    Usage in app/__init__.py:
        from app.terminology import inject_terminology
        app.context_processor(inject_terminology)
    
    Then in templates:
        {{ term.shares }}
        {{ term.portfolio_title }}
    """
    return {
        'term': get_terms(),
        't': t,
        'format_amount': format_amount,
        'format_percentage': format_percentage,
    }


# ============================================
# MIGRATION HELPER
# ============================================

def get_ui_replacements() -> dict:
    """
    Get a dictionary of old terms to new terms for UI migration.
    Useful for automated find/replace in templates.
    
    Returns:
        dict: Mapping of old terms to new terms
    """
    terms = get_terms()
    return {
        # English terms
        'Shares': terms['shares'],
        'shares': terms['shares_lower'],
        'Share': terms['shares_singular'],
        'share': terms['shares_lower'],
        'Equity': terms['equity'],
        'equity': terms['equity_lower'],
        'Phantom Shares': terms['phantom_shares'],
        'phantom shares': terms['phantom_shares'].lower(),
        
        # Italian terms
        'Quote': terms['shares'],
        'quote': terms['shares_lower'],
        'Partecipazione': terms['shares'],
        'partecipazione': terms['shares_lower'],
        
        # Common phrases
        'Equity Portfolio': terms['portfolio_title'],
        'equity portfolio': terms['portfolio_title'].lower(),
        'Total Shares': terms['total_label'],
        'total shares': terms['total_label'].lower(),
    }

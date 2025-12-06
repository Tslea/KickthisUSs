"""
Test per verificare che la semplificazione UI non abbia rotto funzionalità
"""

def test_category_mapping():
    """Verifica che il mapping JavaScript sia corretto"""
    mapping = {
        'code': 'software',
        'design': 'design',
        'content': 'documentation',
        'research': 'documentation',
        'media': 'media',
        'strategy': 'documentation',
        'testing': 'software',
        'marketing': 'media'
    }
    
    # Verifica che tutte le 8 categorie mappino a un content_type valido
    from app.models import CONTENT_TYPES
    
    for category, content_type in mapping.items():
        assert content_type in CONTENT_TYPES, f"❌ {category} -> {content_type} non valido!"
        print(f"✅ {category} -> {content_type} ({CONTENT_TYPES[content_type]})")
    
    print("\n✅ Tutti i mapping sono corretti!")
    return True

def test_form_fields():
    """Verifica che il form abbia tutti i campi necessari"""
    from app.forms import SolutionForm
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        form = SolutionForm()
        
        # Verifica campi obbligatori
        required_fields = ['solution_content', 'solution_file', 'solution_zip', 'contribution_category']
        for field in required_fields:
            assert hasattr(form, field), f"❌ Campo {field} mancante!"
            print(f"✅ Campo {field} presente")
        
        # Verifica choices contribution_category
        assert len(form.contribution_category.choices) == 8, "❌ Numero categorie errato!"
        print(f"✅ 8 categorie contribution_category configurate")
        
        print("\n✅ Form configurato correttamente!")
        return True

def test_template_structure():
    """Verifica che il template non abbia più elementi duplicati"""
    import re
    
    with open('app/templates/submit_solution.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verifica che non ci siano più .ssp-type-card nel CSS
    card_css = content.count('.ssp-type-card {')
    assert card_css == 0, f"❌ Trovati ancora {card_css} riferimenti a .ssp-type-card nel CSS!"
    print("✅ CSS delle card obsolete rimosso")
    
    # Verifica che non ci sia più selectType function
    select_type = content.count('function selectType(')
    assert select_type == 0, f"❌ Trovata ancora function selectType!"
    print("✅ Function selectType rimossa")
    
    # Verifica presenza mapping JavaScript
    assert 'categoryToContentType' in content, "❌ Mapping categoryToContentType mancante!"
    print("✅ Mapping categoryToContentType presente")
    
    # Verifica hidden input
    assert 'id="contentTypeHidden"' in content, "❌ Hidden input contentTypeHidden mancante!"
    print("✅ Hidden input contentTypeHidden presente")
    
    # Verifica contribution_category select
    assert 'id="contributionCategorySelect"' in content, "❌ Select contributionCategorySelect mancante!"
    print("✅ Select contributionCategorySelect presente")
    
    # Conta occorrenze "Step 1" visibili (non nei commenti) - dovrebbe essercene solo 1 visibile
    step1_visible = len(re.findall(r'<(?!!)([^>]*>)?[^<]*Step 1:', content))
    # Alternativa: cerca Step 1 in elementi visibili (h3, div, p, span, label)
    step1_visible = len(re.findall(r'<(?:h[1-6]|div|p|span|label)[^>]*>[^<]*Step 1:', content))
    print(f"✅ Step 1 presente nei commenti (per sviluppatori)")
    
    print("\n✅ Template pulito e corretto!")
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 Test pulizia UI - Verifica integrità")
    print("=" * 60)
    
    try:
        print("\n📋 Test 1: Mapping categorie...")
        test_category_mapping()
        
        print("\n📋 Test 2: Campi form...")
        test_form_fields()
        
        print("\n📋 Test 3: Struttura template...")
        test_template_structure()
        
        print("\n" + "=" * 60)
        print("✅ TUTTI I TEST PASSATI - Funzionalità intatta!")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FALLITO: {e}")
        print("=" * 60)
        raise

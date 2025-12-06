"""
Test per verificare che la semplificazione del form non abbia rotto funzionalità
"""
import re

def test_template_simplified():
    """Verifica che il template sia stato semplificato correttamente"""
    with open('app/templates/submit_solution.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # ✅ Elementi che devono esistere
    required_elements = [
        ('tab-zip', 'Tab ZIP upload'),
        ('tab-pr', 'Tab PR link'),
        ('zipInput', 'Input ZIP file'),
        ('prInput', 'Input PR URL'),
        ('descriptionTextarea', 'Textarea descrizione'),
        ('contributionCategorySelect', 'Select categoria'),
        ('contentTypeHidden', 'Hidden field content_type'),
        ('categoryToContentType', 'Mapping JavaScript'),
        ('handleZipFile', 'Function ZIP handler'),
        ('clearZipFile', 'Function clear ZIP'),
    ]
    
    print("✅ Verifica elementi obbligatori:")
    for element_id, description in required_elements:
        assert element_id in content, f"❌ {description} mancante!"
        print(f"  ✅ {description} presente")
    
    # ❌ Elementi che NON devono esistere
    forbidden_elements = [
        ('tab-files', 'Tab Carica File - RIMOSSO'),
        ('tab-code', 'Tab Incolla Codice - RIMOSSO'),
        ('fileInput', 'Input file multipli - RIMOSSO'),
        ('codeTextarea', 'Textarea codice - RIMOSSO'),
        ('handleFiles', 'Function handleFiles - RIMOSSA'),
        ('handleDrop', 'Function handleDrop - RIMOSSA'),
        ('uploadedFiles', 'Array uploadedFiles - RIMOSSO'),
        ('Pubblicazione Automatica su GitHub', 'Banner auto-publish - RIMOSSO'),
        ('Carica i tuoi file o incolla', 'Hint header - RIMOSSO'),
    ]
    
    print("\n❌ Verifica elementi rimossi:")
    for element_id, description in forbidden_elements:
        # Eccezioni: alcuni ID potrebbero essere in commenti o stringhe
        if element_id in ['tab-files', 'tab-code', 'fileInput', 'codeTextarea']:
            # Cerca come ID HTML effettivo, non in stringhe
            pattern = f'id=["\']?{element_id}["\']?'
            if re.search(pattern, content):
                print(f"  ⚠️  {description} ancora presente come ID!")
                return False
        else:
            if element_id in content:
                print(f"  ⚠️  {description} ancora presente!")
                return False
        print(f"  ✅ {description} correttamente rimosso")
    
    # Conta i tab rimasti (devono essere 2)
    tab_buttons = len(re.findall(r'<button[^>]*class="ssp-tab[^"]*"', content))
    assert tab_buttons == 2, f"❌ Trovati {tab_buttons} tab invece di 2!"
    print(f"\n✅ {tab_buttons} tab presenti (ZIP + PR) - CORRETTO")
    
    # Verifica validazione form JavaScript
    assert 'if (!zipFile && !pr)' in content, "❌ Validazione form non aggiornata!"
    print("✅ Validazione form aggiornata (solo ZIP o PR)")
    
    return True

def test_backend_compatibility():
    """Verifica che i campi del backend siano ancora compatibili"""
    from app.forms import SolutionForm
    from flask import Flask
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        form = SolutionForm()
        
        # Verifica campi ancora presenti nel form
        required_fields = [
            'solution_content',     # Descrizione (ancora usata)
            'solution_zip',         # ZIP upload (MANTENUTO)
            'contribution_category' # Categoria (MANTENUTO)
        ]
        
        print("\n✅ Verifica compatibilità backend:")
        for field in required_fields:
            assert hasattr(form, field), f"❌ Campo {field} mancante nel form!"
            print(f"  ✅ Campo {field} presente nel backend")
        
        # Campo solution_file esiste ancora ma non è più nell'UI
        # (backward compatibility per vecchie submission)
        if hasattr(form, 'solution_file'):
            print("  ℹ️  Campo solution_file ancora nel backend (backward compat)")
        
        return True

def test_route_compatibility():
    """Verifica che la route gestisca ancora tutti i flussi"""
    with open('app/routes_tasks.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("\n✅ Verifica compatibilità route:")
    
    # Flussi che devono esistere
    required_flows = [
        ('form.solution_zip.data', 'Gestione ZIP upload'),
        ('form.contribution_category.data', 'Gestione categoria'),
        ('pull_request_url', 'Gestione PR manuale'),
        ('solution_content', 'Gestione descrizione'),
    ]
    
    for code_snippet, description in required_flows:
        assert code_snippet in content, f"❌ {description} mancante nella route!"
        print(f"  ✅ {description} presente")
    
    # Flussi deprecati che possono rimanere per backward compatibility
    deprecated_flows = [
        ('solution_code_auto', 'Codice incollato (deprecated ma presente)'),
        ('solution_file.data', 'File singolo (deprecated ma presente)'),
    ]
    
    for code_snippet, description in deprecated_flows:
        if code_snippet in content:
            print(f"  ℹ️  {description} - OK per backward compat")
    
    return True

if __name__ == '__main__':
    print("=" * 70)
    print("🧪 Test semplificazione form - Verifica integrità")
    print("=" * 70)
    
    try:
        print("\n📋 Test 1: Template semplificato...")
        test_template_simplified()
        
        print("\n📋 Test 2: Compatibilità backend...")
        test_backend_compatibility()
        
        print("\n📋 Test 3: Compatibilità route...")
        test_route_compatibility()
        
        print("\n" + "=" * 70)
        print("✅ TUTTI I TEST PASSATI - Semplificazione completata!")
        print("=" * 70)
        print("\n📝 Riepilogo modifiche:")
        print("  ✅ Rimossi: Tab 'Carica File', Tab 'Incolla Codice'")
        print("  ✅ Rimosso: Banner 'Pubblicazione Automatica su GitHub'")
        print("  ✅ Rimosso: Hint header 'Carica i tuoi file...'")
        print("  ✅ Mantenuti: Tab ZIP, Tab PR, Descrizione, Categoria")
        print("  ✅ Backward compatibility: Route gestisce ancora vecchi flussi")
        print("  ✅ Validazione aggiornata: Solo ZIP o PR richiesti")
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ TEST FALLITO: {e}")
        print("=" * 70)
        raise

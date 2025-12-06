"""
Test diagnostico per problemi UI delle Free Proposals
Questo test verifica che la pagina si carichi correttamente e che tutti gli elementi siano presenti.
"""
import pytest
from app.models import User, Project, Task, ProjectEquity
from app.extensions import db as _db
from flask_login import login_user


def test_propose_page_loads_with_tasks(client, db):
    """Test che la pagina si carichi con task disponibili"""
    # Crea utente e progetto
    creator = User(username='creator', email='creator@test.com')
    creator.set_password('password123')
    creator.email_verified = True
    _db.session.add(creator)
    _db.session.commit()
    
    project = Project(
        name='Test Project',
        description='Test description',
        creator_id=creator.id,
        category='tech',
        status='open'
    )
    _db.session.add(project)
    _db.session.commit()
    
    # Crea equity per il creator
    equity = ProjectEquity(
        project_id=project.id,
        user_id=creator.id,
        equity_percentage=100.0,
        earned_from='creator'
    )
    _db.session.add(equity)
    
    # Crea alcuni task con equity
    task1 = Task(
        project_id=project.id,
        creator_id=creator.id,
        title='Task 1',
        description='Test task 1',
        status='open',
        equity_reward=5.0
    )
    task2 = Task(
        project_id=project.id,
        creator_id=creator.id,
        title='Task 2',
        description='Test task 2',
        status='open',
        equity_reward=3.0
    )
    _db.session.add_all([task1, task2])
    _db.session.commit()
    
    # Login come developer
    developer = User(username='developer', email='dev@test.com')
    developer.set_password('password123')
    developer.email_verified = True
    _db.session.add(developer)
    _db.session.commit()
    
    # Esegui login
    client.post('/auth/login', data={
        'email': 'dev@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    # GET sulla pagina
    response = client.get(f'/project/{project.id}/propose-free', follow_redirects=True)
    
    print("\n" + "="*80)
    print("DIAGNOSTICA PAGINA FREE PROPOSALS")
    print("="*80)
    
    # Verifica status code
    print(f"\n[OK] Status Code: {response.status_code}")
    
    # Converti response in stringa
    html = response.data.decode('utf-8')
    
    # DEBUG: Vediamo il titolo per capire quale pagina è stata caricata
    if '<title>' in html:
        title_start = html.find('<title>') + 7
        title_end = html.find('</title>')
        page_title = html[title_start:title_end]
        print(f"[DEBUG] Titolo pagina: {page_title}")
    
    # DEBUG: Vediamo se c'è un messaggio flash
    if 'alert' in html.lower():
        print("[DEBUG] Trovati messaggi alert nella pagina")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Verifica elementi critici presenti
    checks = {
        'Breadcrumb presente': 'breadcrumb' in html,
        'Header "Proponi Soluzione Libera"': 'Proponi Soluzione Libera' in html,
        'Radio "Aggrega Task Esistenti"': 'Aggrega Task Esistenti' in html or 'multi_task' in html,
        'Radio "Proponi Nuovo Task"': 'Proponi Nuovo Task' in html or 'new_task' in html,
        'Sezione multi-task presente': 'multi-task-section' in html,
        'Sezione new-task presente': 'new-task-section' in html,
        'Task 1 presente': 'Task 1' in html,
        'Task 2 presente': 'Task 2' in html,
        'Checkbox task presente': 'task-checkbox' in html,
        'JavaScript presente': '<script>' in html,
        'Pulsante submit presente': 'type="submit"' in html or 'Invia Proposta' in html,
    }
    
    print("\n[*] ELEMENTI HTML TROVATI:")
    for check_name, check_result in checks.items():
        status = "[+]" if check_result else "[-]"
        print(f"  {status} {check_name}")
        if not check_result:
            print(f"     [!] MANCANTE!")
    
    # Verifica equity disponibile
    if 'Equity disponibile del progetto:' in html:
        print("\n[OK] Equity disponibile mostrata")
    else:
        print("\n[-] Equity disponibile NON mostrata")
    
    # Verifica presenza classi Bootstrap
    bootstrap_classes = ['d-none', 'form-check', 'card', 'btn-primary']
    print("\n[*] CLASSI BOOTSTRAP:")
    for cls in bootstrap_classes:
        if cls in html:
            print(f"  [+] {cls} presente")
        else:
            print(f"  [-] {cls} MANCANTE")
    
    # Verifica presenza getElementById nel JavaScript
    if 'getElementById' in html:
        print("\n[OK] JavaScript con getElementById presente")
        # Conta quanti getElementById ci sono
        count = html.count('getElementById')
        print(f"  Trovati {count} chiamate a getElementById")
    else:
        print("\n[-] JavaScript getElementById MANCANTE")
    
    # Verifica stile inline problematico
    if 'style="display: none"' in html:
        print("\n[!] WARNING: Trovato style='display: none' inline (puo causare conflitti)")
        print("  Dovrebbe usare solo classi Bootstrap (d-none)")
    else:
        print("\n[OK] Nessuno style='display: none' inline trovato")
    
    # Verifica che le sezioni abbiano d-none
    if 'id="new-task-section" class="d-none"' in html or ('id="new-task-section"' in html and 'd-none' in html):
        print("[+] Sezione new-task ha classe d-none")
    else:
        print("[!] new-task-section potrebbe non avere d-none")
    
    print("\n" + "="*80)
    print("FINE DIAGNOSTICA")
    print("="*80 + "\n")
    
    # Assert finali
    assert response.status_code == 200
    assert 'Proponi Soluzione Libera' in html
    assert 'multi-task-section' in html
    assert 'Task 1' in html or 'Task 2' in html, "Almeno un task dovrebbe essere visibile"


def test_propose_page_without_tasks(client, db):
    """Test che la pagina funzioni anche senza task disponibili"""
    # Crea utente e progetto SENZA task
    creator = User(username='creator2', email='creator2@test.com')
    creator.set_password('password123')
    _db.session.add(creator)
    _db.session.commit()
    
    project = Project(
        name='Empty Project',
        description='Project without tasks',
        creator_id=creator.id,
        category='tech',
        status='open'
    )
    _db.session.add(project)
    _db.session.commit()
    
    # Crea equity
    equity = ProjectEquity(
        project_id=project.id,
        user_id=creator.id,
        equity_percentage=100.0,
        earned_from='creator'
    )
    _db.session.add(equity)
    _db.session.commit()
    
    # Login come developer
    developer = User(username='developer2', email='dev2@test.com')
    developer.set_password('password123')
    _db.session.add(developer)
    _db.session.commit()
    
    # Esegui login
    client.post('/auth/login', data={
        'email': 'dev2@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    response = client.get(f'/project/{project.id}/propose-free')
    
    print("\n" + "="*80)
    print("TEST PROGETTO SENZA TASK")
    print("="*80)
    
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    
    # Dovrebbe comunque mostrare la pagina
    assert 'Proponi Soluzione Libera' in html
    
    # Dovrebbe mostrare warning
    if 'Nessun task disponibile' in html:
        print("✓ Warning 'Nessun task disponibile' presente")
    else:
        print("✗ Warning mancante - potrebbe confondere l'utente")
    
    # La sezione nuovo task dovrebbe essere disponibile
    assert 'new-task-section' in html
    assert 'Proponi Nuovo Task' in html
    
    print("✓ Pagina carica correttamente anche senza task")
    print("="*80 + "\n")


def test_javascript_logic(client, db):
    """Test che verifica la logica JavaScript nel template"""
    # Setup base
    creator = User(username='creator3', email='creator3@test.com')
    creator.set_password('password123')
    creator.email_verified = True
    _db.session.add(creator)
    _db.session.commit()
    
    project = Project(
        name='JS Test Project',
        description='Test JS',
        creator_id=creator.id,
        category='tech',
        status='open'
    )
    _db.session.add(project)
    _db.session.commit()  # Commit project first to get project.id
    
    equity = ProjectEquity(
        project_id=project.id,
        user_id=creator.id,
        equity_percentage=100.0,
        earned_from='creator'
    )
    _db.session.add(equity)
    _db.session.commit()
    
    developer = User(username='developer3', email='dev3@test.com')
    developer.set_password('password123')
    developer.email_verified = True
    _db.session.add(developer)
    _db.session.commit()
    
    # Esegui login
    client.post('/auth/login', data={
        'email': 'dev3@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    response = client.get(f'/project/{project.id}/propose-free', follow_redirects=True)
    html = response.data.decode('utf-8')
    
    print("\n" + "="*80)
    print("ANALISI JAVASCRIPT")
    print("="*80)
    
    # Considera solo lo script inline della pagina (ignora quelli globali del layout)
    js_source = html
    marker = 'FREE PROPOSALS - JavaScript Functions'
    if marker in html:
        start = html.index(marker)
        end = html.find('</script>', start)
        js_source = html[start:end]

    # Verifica presenza funzioni chiave (pattern nuovo come submit_solution.html)
    js_elements = {
        'NO DOMContentLoaded': 'DOMContentLoaded' not in js_source,  # Non dovrebbe esserci più
        'switchProposalType': 'switchProposalType' in js_source,  # Nuova funzione
        'updateTaskSummary': 'updateTaskSummary' in js_source,
        'updateEquityPreview': 'updateEquityPreview' in js_source,
        'updateCharCount': 'updateCharCount' in js_source,
        'validateProposalForm': 'validateProposalForm' in js_source,
        'classList.remove': 'classList.remove' in js_source,
        'classList.add': 'classList.add' in js_source,
    }
    
    print("\n[*] FUNZIONI JAVASCRIPT:")
    for element, present in js_elements.items():
        status = "[+]" if present else "[-]"
        print(f"  {status} {element}")
    
    # Verifica che non ci siano conflitti style.display (dovrebbe usare solo classList)
    if 'style.display' in html:
        print("\n[!] ATTENZIONE: Trovato 'style.display' nel JavaScript")
        print("  Questo puo causare conflitti con Bootstrap!")
    else:
        print("\n[OK] JavaScript usa solo classList (corretto)")
    
    print("="*80 + "\n")
    
    assert all(js_elements.values()), "Mancano elementi JavaScript critici"


if __name__ == '__main__':
    print("\n🧪 Esegui questo test con: pytest tests/test_free_proposals_ui.py -v -s\n")

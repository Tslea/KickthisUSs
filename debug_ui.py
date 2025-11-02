"""
Script di debug per verificare il rendering della pagina free proposals
Disabilita temporaneamente il JavaScript per vedere se il problema è lì
"""
from app import create_app
from app.extensions import db
from app.models import Project, User

app = create_app()

with app.app_context():
    # Prendi il primo progetto
    project = Project.query.first()
    
    if not project:
        print("❌ Nessun progetto trovato nel database!")
        exit(1)
    
    print(f"\n✓ Progetto trovato: {project.name}")
    print(f"  ID: {project.id}")
    print(f"  Status: {project.status}")
    print(f"  Creator ID: {project.creator_id}")
    
    # Verifica task disponibili
    from app.models import Task
    tasks = Task.query.filter_by(project_id=project.id, status='open').all()
    print(f"\n✓ Task disponibili: {len(tasks)}")
    for task in tasks[:3]:  # Mostra solo i primi 3
        print(f"  - {task.title} (Equity: {task.equity_reward}%)")
    
    # Verifica equity disponibile
    available_equity = project.get_available_equity()
    print(f"\n✓ Equity disponibile: {available_equity}%")
    
    # Verifica utenti
    users = User.query.filter(User.id != project.creator_id).limit(3).all()
    print(f"\n✓ Utenti che possono proporre: {len(users)}")
    for user in users:
        print(f"  - {user.username} (ID: {user.id})")
    
    if users:
        test_user = users[0]
        print(f"\n📝 URL per testare nel browser:")
        print(f"   http://localhost:5000/project/{project.id}/propose-free")
        print(f"\n   Login con:")
        print(f"   - Email: {test_user.email}")
        print(f"   - Username: {test_user.username}")
        print(f"\n⚠️  IMPORTANTE: Apri il browser con DevTools (F12)")
        print(f"   e guarda nella Console per errori JavaScript!")
    else:
        print("\n❌ Nessun utente disponibile per il test!")
        print("   Crea un utente diverso dal creator del progetto")

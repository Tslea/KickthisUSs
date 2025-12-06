#!/usr/bin/env python3
"""Script per testare il token GitHub"""
import os
from dotenv import load_dotenv

# Carica .env
load_dotenv()

token = os.environ.get('GITHUB_TOKEN')
print(f"Token dal .env: {token[:10]}...{token[-10:]}" if token else "Token non trovato!")
print(f"Lunghezza token: {len(token)}" if token else "")

# Prova con PyGithub
try:
    from github import Github
    
    print("\n🔍 Testando connessione con GitHub...")
    g = Github(token)
    
    # Get current user
    user = g.get_user()
    print(f"✅ Token VALIDO!")
    print(f"   Username: {user.login}")
    print(f"   Name: {user.name}")
    print(f"   Email: {user.email}")
    print(f"   Type: {user.type}")
    
    # Verifica organizzazione
    org_name = os.environ.get('GITHUB_ORG', 'kickthisuss-projects')
    print(f"\n🔍 Verifico accesso all'organizzazione '{org_name}'...")
    try:
        org = g.get_organization(org_name)
        print(f"✅ Accesso all'organizzazione confermato!")
        print(f"   Nome: {org.name}")
        print(f"   Repos pubblici: {org.public_repos}")
        
        # Lista repos
        print(f"\n📦 Repository nell'organizzazione:")
        repos = org.get_repos()
        for repo in list(repos)[:5]:  # primi 5
            print(f"   - {repo.name} ({'privato' if repo.private else 'pubblico'})")
            
    except Exception as e:
        print(f"❌ Errore accesso organizzazione: {e}")
        print(f"   Tipo errore: {type(e).__name__}")
        
except Exception as e:
    print(f"\n❌ ERRORE: Token NON valido o PyGithub non installato")
    print(f"   Messaggio: {e}")
    print(f"   Tipo: {type(e).__name__}")
    
    # Se è 401, il token è scaduto/invalido
    if '401' in str(e):
        print("\n💡 SOLUZIONE:")
        print("   Il token è scaduto o revocato.")
        print("   1. Vai su https://github.com/settings/tokens")
        print("   2. Genera un nuovo token con permessi: repo, admin:org")
        print("   3. Aggiorna GITHUB_TOKEN nel file .env")

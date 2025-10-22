"""
Script di setup per configurare l'integrazione GitHub
Esegui questo script dopo aver configurato le variabili d'ambiente
"""
import os
import sys
from services.github_service import get_github_service
from config.github_config import GITHUB_ENABLED, GITHUB_TOKEN, GITHUB_ORG

def verify_github_token():
    """Verifica che il token GitHub sia valido"""
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not configured in .env")
        return False
    
    try:
        github_service = get_github_service()
        url = f"{github_service.api_base}/user"
        response = github_service._make_request('GET', url)
        
        if response:
            user_data = response.json()
            print(f"✓ GitHub token valid for user: {user_data['login']}")
            return True
        else:
            print("❌ Invalid GitHub token")
            return False
    except Exception as e:
        print(f"❌ Error verifying token: {e}")
        return False

def verify_organization():
    """Verifica che l'organizzazione GitHub esista"""
    try:
        github_service = get_github_service()
        url = f"{github_service.api_base}/orgs/{GITHUB_ORG}"
        response = github_service._make_request('GET', url)
        
        if response:
            org_data = response.json()
            print(f"✓ Organization found: {org_data['name']}")
            return True
        else:
            print(f"❌ Organization '{GITHUB_ORG}' not found or no access")
            return False
    except Exception as e:
        print(f"❌ Error verifying organization: {e}")
        return False

def create_template_repo():
    """Crea repository template se non esiste"""
    try:
        github_service = get_github_service()
        
        # Verifica se esiste già
        url = f"{github_service.api_base}/repos/{GITHUB_ORG}/project-template"
        response = github_service._make_request('GET', url)
        
        if response:
            print("✓ Template repository already exists")
            return True
        
        # Crea template
        print("Creating template repository...")
        payload = {
            'name': 'project-template',
            'description': 'Template repository for KickThisUSS projects',
            'private': False,
            'auto_init': True,
            'is_template': True
        }
        
        url = f"{github_service.api_base}/orgs/{GITHUB_ORG}/repos"
        response = github_service._make_request('POST', url, json=payload)
        
        if response:
            print("✓ Template repository created")
            return True
        else:
            print("❌ Failed to create template repository")
            return False
            
    except Exception as e:
        print(f"❌ Error with template repository: {e}")
        return False

def setup_database():
    """Esegue migration database per campi GitHub"""
    print("\n=== Database Setup ===")
    print("Running database migrations...")
    
    try:
        os.system("flask db migrate -m 'Add GitHub integration fields'")
        os.system("flask db upgrade")
        print("✓ Database migrations completed")
        return True
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        print("You may need to run manually: flask db migrate && flask db upgrade")
        return False

def main():
    print("=== KickThisUSS GitHub Integration Setup ===\n")
    
    if not GITHUB_ENABLED:
        print("⚠️  GitHub integration is disabled (GITHUB_ENABLED=false)")
        print("Set GITHUB_ENABLED=true in .env to enable")
        return
    
    print("GitHub integration is enabled\n")
    
    print("=== Verifying Configuration ===")
    checks = [
        ("GitHub Token", verify_github_token),
        ("GitHub Organization", verify_organization),
        ("Template Repository", create_template_repo),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        results.append(check_func())
    
    # Database setup
    results.append(setup_database())
    
    print("\n=== Setup Summary ===")
    if all(results):
        print("✓ All checks passed! GitHub integration is ready.")
        print("\nNext steps:")
        print("1. Start Celery worker: celery -A tasks.celery worker --loglevel=info")
        print("2. Start Flask app: flask run")
    else:
        print("❌ Some checks failed. Please fix the issues and run setup again.")
        sys.exit(1)

if __name__ == "__main__":
    main()

import requests
import json

# Test della votazione
def test_vote():
    base_url = "http://127.0.0.1:5000"
    
    # Prima proviamo senza autenticazione
    print("=== Test senza autenticazione ===")
    response = requests.post(f"{base_url}/vote_project/3")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Ora proviamo a fare login e poi votare
    print("\n=== Test con login ===")
    session = requests.Session()
    
    # Ottieni la pagina di login per eventuale CSRF token
    login_page = session.get(f"{base_url}/auth/login")
    print(f"Login page status: {login_page.status_code}")
    
    # Prova a fare login
    login_data = {
        'email': 'test@test.com',
        'password': 'password123'
    }
    
    login_response = session.post(f"{base_url}/auth/login", data=login_data)
    print(f"Login status: {login_response.status_code}")
    print(f"Login response length: {len(login_response.text)}")
    
    # Ora prova a votare con la sessione autenticata
    vote_response = session.post(f"{base_url}/vote_project/3")
    print(f"Vote status: {vote_response.status_code}")
    print(f"Vote response: {vote_response.text}")

# Test GitHub integration
def test_github_integration():
    """Test completo dell'integrazione GitHub"""
    base_url = "http://127.0.0.1:5000"
    
    print("\n=== Test GitHub Integration ===")
    
    # Test API status
    print("\n1. Testing GitHub status endpoint...")
    response = requests.get(f"{base_url}/api/github/project/1/files")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"GitHub enabled: {data.get('enabled', False)}")
        print(f"Files count: {len(data.get('files', []))}")
    
    # Test solution preview
    print("\n2. Testing solution preview...")
    response = requests.get(f"{base_url}/api/github/solution/1/preview")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Preview generated: {data.get('preview') is not None}")
    
    # Test sync status
    print("\n3. Testing solution sync status...")
    response = requests.get(f"{base_url}/api/github/solution/1/status")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Synced: {data.get('synced')}")
        print(f"Branch: {data.get('branch')}")
        print(f"PR URL: {data.get('pr_url')}")

def test_file_upload_organization():
    """Test organizzazione file hardware"""
    from utils.hardware_parser import HardwareFileHandler
    
    print("\n=== Test Hardware File Organization ===")
    
    handler = HardwareFileHandler()
    
    test_files = [
        'schematic.pdf',
        'board.kicad_pcb',
        'circuit.kicad_sch',
        'case.stl',
        'case_top.step',
        'bom.csv',
        'prototype.jpg'
    ]
    
    for filename in test_files:
        category = handler._categorize_file(filename)
        print(f"{filename:20} -> {category}")

if __name__ == "__main__":
    # Test originali
    test_vote()
    
    # Test GitHub integration
    test_github_integration()
    test_file_upload_organization()

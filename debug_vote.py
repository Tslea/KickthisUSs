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

if __name__ == "__main__":
    test_vote()

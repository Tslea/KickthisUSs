# test_ai_tasks.py
"""
Test specifico per la generazione di task AI
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_ai_task_generation():
    """Testa la generazione di task AI tramite API"""
    print("🤖 Testando generazione task AI...")
    
    # Simula una chiamata diretta al servizio AI
    try:
        from app.ai_services import generate_suggested_tasks, AI_SERVICE_AVAILABLE
        
        if not AI_SERVICE_AVAILABLE:
            print("❌ Servizio AI non disponibile")
            return
        
        # Test con dati di esempio
        pitch = "Una piattaforma per condividere ricette vegane con la community"
        category = "Social"
        description = "Vogliamo creare un social network per amanti della cucina vegana"
        existing_tasks = []
        
        tasks = generate_suggested_tasks(pitch, category, description, existing_tasks)
        
        if tasks:
            print(f"✅ Generati {len(tasks)} task")
            for i, task in enumerate(tasks, 1):
                print(f"   {i}. {task.get('title')} ({task.get('task_type')}) - {task.get('equity_reward')}% equity")
                if task.get('task_type') == 'validation':
                    print(f"      Ipotesi: {task.get('hypothesis', 'N/A')}")
                    print(f"      Metodo: {task.get('test_method', 'N/A')}")
        else:
            print("❌ Nessun task generato")
            
    except Exception as e:
        print(f"❌ Errore nel test: {e}")

if __name__ == "__main__":
    print("🧪 Test Generazione Task AI")
    print("=" * 40)
    test_ai_task_generation()

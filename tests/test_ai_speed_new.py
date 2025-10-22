#!/usr/bin/env python3
"""
Test velocità nuovo modello DeepSeek R1-Distill-Llama-70B
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Carica environment variables
load_dotenv()

# Aggiungi il path del progetto
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app import create_app
    from app.ai_services import AI_SERVICE_AVAILABLE, analyze_with_ai
    
    print("🚀 Test Nuovo Modello DeepSeek R1-Distill-Llama-70B")
    print("=" * 60)
    
    # Crea l'app context
    app = create_app()
    
    with app.app_context():
        if not AI_SERVICE_AVAILABLE:
            print("❌ AI Service non disponibile")
            print("💡 Assicurati che DEEPSEEK_API_KEY sia configurata nel file .env")
            exit(1)
        
        print("✅ AI Service disponibile")
        print("🔧 Modello utilizzato: deepseek-r1-distill-llama-70b")
        
        # Test di velocità
        test_prompts = [
            "Genera una breve analisi per un'app di delivery food",
            "Crea una lista di 3 task per sviluppare un MVP",
            "Analizza la fattibilità di un social network per studenti"
        ]
        
        total_time = 0
        successful_tests = 0
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n🧪 Test {i}/3: {prompt[:50]}...")
            
            try:
                start_time = time.time()
                result = analyze_with_ai(prompt, max_tokens=200, temperature=0.3)
                end_time = time.time()
                
                response_time = end_time - start_time
                total_time += response_time
                successful_tests += 1
                
                print(f"⚡ Tempo risposta: {response_time:.2f}s")
                print(f"📝 Risultato: {result[:100]}...")
                
                if response_time < 20:
                    print("✅ VELOCITÀ OTTIMA (<20s)")
                elif response_time < 40:
                    print("✅ VELOCITÀ BUONA (<40s)")
                else:
                    print("⚠️ VELOCITÀ LENTA (>40s)")
                    
            except Exception as e:
                print(f"❌ Errore: {e}")
        
        if successful_tests > 0:
            avg_time = total_time / successful_tests
            print(f"\n📊 RISULTATI FINALI:")
            print(f"✅ Test completati: {successful_tests}/{len(test_prompts)}")
            print(f"⚡ Tempo medio risposta: {avg_time:.2f}s")
            
            # Confronto con il modello precedente
            if avg_time < 15:
                improvement = "80-90% più veloce del deepseek-chat"
            elif avg_time < 25:
                improvement = "60-80% più veloce del deepseek-chat"
            elif avg_time < 40:
                improvement = "40-60% più veloce del deepseek-chat"
            else:
                improvement = "potrebbe essere più lento del deepseek-chat"
            
            print(f"🚀 Miglioramento stimato: {improvement}")
            
            if avg_time < 20:
                print("\n🎯 OTTIMIZZAZIONE RIUSCITA!")
                print("Il nuovo modello deepseek-r1-distill-llama-70b è significativamente più veloce")
                print("mantenendo alta qualità per le funzionalità business di KICKTHISUSS")
            else:
                print("\n⚠️ Potrebbe essere necessaria ulteriore ottimizzazione")
        else:
            print("\n❌ Tutti i test sono falliti")
                
except ImportError as e:
    print(f"❌ Errore importazione: {e}")
    print("💡 Assicurati di essere nella directory corretta del progetto")
except Exception as e:
    print(f"❌ Errore generale: {e}")

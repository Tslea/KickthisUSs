#!/usr/bin/env python
"""
Test rapido per verificare che Grok sia configurato correttamente
"""
from app import create_app
from app.ai_services import AI_SERVICE_AVAILABLE, CURRENT_PROVIDER, CURRENT_MODEL

print("=" * 60)
print("🧪 TEST CONFIGURAZIONE GROK")
print("=" * 60)

app = create_app()

with app.app_context():
    print(f"\n✅ AI Service Disponibile: {AI_SERVICE_AVAILABLE}")
    print(f"✅ Provider Corrente: {CURRENT_PROVIDER}")
    print(f"✅ Modello Corrente: {CURRENT_MODEL}")
    
    if CURRENT_PROVIDER == 'grok' and CURRENT_MODEL == 'grok-4-fast':
        print("\n🎉 SUCCESSO! Grok 4 Fast è configurato correttamente!")
    elif CURRENT_PROVIDER == 'deepseek':
        print("\n⚠️  ATTENZIONE: Stai usando DeepSeek (fallback)")
        print("   Verifica che GROK_API_KEY sia configurata in .env")
    else:
        print(f"\n❌ ERRORE: Provider inaspettato: {CURRENT_PROVIDER}")
    
    print("\n" + "=" * 60)

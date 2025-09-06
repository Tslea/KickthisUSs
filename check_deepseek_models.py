#!/usr/bin/env python3
"""
Script per verificare i modelli disponibili su DeepSeek API
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

# Carica variabili ambiente
load_dotenv()

# Configurazione API DeepSeek
api_key = os.getenv('DEEPSEEK_API_KEY')
if not api_key:
    print("❌ DEEPSEEK_API_KEY non trovata nel file .env")
    exit(1)

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com/v1"
)

def check_available_models():
    """Controlla i modelli disponibili su DeepSeek"""
    try:
        print("🔍 Controllando modelli disponibili su DeepSeek API...")
        
        # Lista modelli disponibili
        models = client.models.list()
        print("\n📋 Modelli disponibili:")
        
        for model in models.data:
            print(f"  - {model.id}")
            if 'r1' in model.id.lower() or 'distill' in model.id.lower():
                print(f"    ⭐ CANDIDATO: {model.id}")
        
        return models.data
        
    except Exception as e:
        print(f"❌ Errore nel recuperare modelli: {e}")
        return []

def test_model(model_name):
    """Testa un modello specifico"""
    try:
        print(f"\n🧪 Testando modello: {model_name}")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Ciao, rispondi brevemente in italiano"}],
            max_tokens=50,
            temperature=0.1
        )
        
        print(f"✅ Modello {model_name} funziona!")
        print(f"Risposta: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ Modello {model_name} non funziona: {e}")
        return False

if __name__ == "__main__":
    print("🚀 KICKTHISUSS - Verifica Modelli DeepSeek")
    print("="*50)
    
    # Lista tutti i modelli
    models = check_available_models()
    
    if not models:
        print("\n❌ Impossibile recuperare lista modelli. Controllo manuale...")
        
        # Test modelli comuni DeepSeek
        common_models = [
            "deepseek-chat",
            "deepseek-coder", 
            "deepseek-reasoner",
            "deepseek-r1",
            "deepseek-r1-distill-qwen-32b",
            "deepseek-r1-distill-qwen-14b",
            "deepseek-r1-distill-qwen-7b",
            "deepseek-r1-distill-llama-70b",
            "deepseek-r1-lite-preview"
        ]
        
        print(f"\n🔄 Testando {len(common_models)} modelli comuni...")
        working_models = []
        
        for model in common_models:
            if test_model(model):
                working_models.append(model)
        
        print(f"\n✅ Modelli funzionanti: {len(working_models)}")
        for model in working_models:
            print(f"  - {model}")
            
        if working_models:
            fastest_model = working_models[0]  # Il primo che funziona
            print(f"\n🎯 RACCOMANDAZIONE: Usa '{fastest_model}'")
        else:
            print("\n⚠️  Nessun modello funziona! Verifica le credenziali API.")
    
    else:
        print(f"\n✅ Trovati {len(models)} modelli disponibili")
        
        # Testa i modelli R1 se disponibili
        r1_models = [m.id for m in models if 'r1' in m.id.lower()]
        
        if r1_models:
            print(f"\n🎯 Modelli R1 disponibili: {len(r1_models)}")
            for model in r1_models:
                test_model(model)
        else:
            print("\n⚠️  Nessun modello R1 trovato, testando deepseek-chat...")
            test_model("deepseek-chat")

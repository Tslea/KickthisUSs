# app/ai_services.py
import os
import json
import httpx
from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIStatusError
from dotenv import load_dotenv
from flask import current_app
from datetime import datetime, timezone

# Carica le variabili dal file .env
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

client = None
AI_SERVICE_AVAILABLE = False

if DEEPSEEK_API_KEY:
    try:
        client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            http_client=httpx.Client(proxies={})
        )
        AI_SERVICE_AVAILABLE = True
        print("--- Servizio AI (DeepSeek) inizializzato correttamente ---")
    except Exception as e:
        print(f"ERRORE: Inizializzazione client DeepSeek fallita: {e}")
else:
    print("--- AVVISO: DEEPSEEK_API_KEY non trovata in .env. Servizio AI non disponibile. ---")

def analyze_with_ai(prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """Funzione generica per analisi con AI"""
    if not AI_SERVICE_AVAILABLE or client is None:
        current_app.logger.warning("AI Service not available for analysis")
        return ""

    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        return chat_completion.choices[0].message.content.strip()
    except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as api_err:
        current_app.logger.error(f"Errore API DeepSeek (analisi generica): {api_err}", exc_info=True)
        return ""
    except Exception as e:
        current_app.logger.error(f"Errore imprevisto chiamata DeepSeek (analisi generica): {e}", exc_info=True)
        return ""

def generate_project_details_from_pitch(pitch: str, category: str) -> dict:
    if not AI_SERVICE_AVAILABLE or client is None:
        raise ConnectionError("DeepSeek AI Service non disponibile o non configurato.")

    system_prompt = """Sei un assistente esperto nell'analisi di idee di progetto. Data un'idea (pitch) e una categoria, genera:
1.  Un nome accattivante e conciso per il progetto (massimo 10-15 parole).
2.  Una descrizione dettagliata del progetto (2-3 paragrafi) che espanda l'idea originale, evidenziando potenzialità e obiettivi.
3.  Un "pitch riscritto" che sia una versione migliorata, più chiara e coinvolgente dell'idea originale (massimo 100 parole).
Rispondi ESCLUSIVAMENTE in formato JSON valido con le chiavi "name", "description", "rewritten_pitch". Non aggiungere spiegazioni o testo prima o dopo il JSON."""
    
    user_prompt = f'''Pitch: "{pitch}"
Categoria: "{category}"'''

    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        response_content = chat_completion.choices[0].message.content
        
        # Controllo se la risposta è vuota o non valida
        if not response_content or not response_content.strip():
            current_app.logger.error("Risposta DeepSeek vuota")
            # Restituisce un fallback con dati di base
            return {
                "title": "Nuovo Progetto",
                "description": pitch,
                "requirements": ["Definire requisiti specifici"],
                "timeline": "Da definire",
                "budget_estimate": "Da valutare"
            }
        
        return json.loads(response_content)
    except json.JSONDecodeError as json_err:
        current_app.logger.error(f"Errore parsing JSON DeepSeek: {json_err}. Risposta: {response_content[:200]}...")
        # Fallback in caso di JSON non valido
        return {
            "title": "Nuovo Progetto",
            "description": pitch,
            "requirements": ["Definire requisiti specifici"],
            "timeline": "Da definire",
            "budget_estimate": "Da valutare"
        }
    except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as api_err:
        current_app.logger.error(f"Errore API DeepSeek (dettagli): {api_err}", exc_info=True)
        raise ConnectionError(f"Errore API DeepSeek: {api_err}")
    except Exception as e:
        current_app.logger.error(f"Errore imprevisto chiamata DeepSeek (dettagli): {e}", exc_info=True)
        raise Exception(f"Errore imprevisto durante l'analisi AI: {e}")

def generate_suggested_tasks(pitch: str, category: str, description: str, existing_tasks: list = None) -> list[dict]:
    if not AI_SERVICE_AVAILABLE or client is None:
        return []  # Restituisce lista vuota invece di dizionario

    # Informazioni contestuali sui task esistenti
    existing_context = ""
    if existing_tasks:
        existing_context = f"\n\nTask già esistenti nel progetto:\n"
        for task in existing_tasks:
            existing_context += f"- {task.get('title', 'N/A')} (Tipo: {task.get('task_type', 'N/A')}, Equity: {task.get('equity_reward', 'N/A')}%)\n"
    
    system_prompt = f"""Sei un esperto Product Manager e Business Analyst specializzato nella creazione di backlog di task per progetti innovativi.
Il tuo obiettivo è definire task strategici, concreti e ben bilanciati per un progetto, considerando il contesto completo.

CONTESTO PROGETTI SIMILI:
- Progetti Tech: spesso richiedono task di architettura (5-8% equity), implementazione core (3-6% equity), testing (2-4% equity)
- Progetti Social: focus su community building (4-7% equity), user research (3-5% equity), content strategy (2-4% equity)
- Progetti Business: analisi di mercato (4-6% equity), business model validation (5-8% equity), prototyping (3-5% equity)

REGOLE PER L'EQUITY:
- Task 'proposal' (ideazione/design): 1-4% equity (basato su complessità strategica)
- Task 'implementation' (sviluppo concreto): 3-8% equity (basato su complessità tecnica)
- Task 'validation' (esperimenti): 2-5% equity (basato su importanza strategica)
- Task critici per il successo del progetto: +1-2% equity bonus
- Task che richiedono competenze specialistiche: +1-2% equity bonus

TIPI DI TASK:
1. **'proposal'**: Ideazione, design, pianificazione, ricerca, definizione di strategie
2. **'implementation'**: Sviluppo, creazione, costruzione, configurazione, coding
3. **'validation'**: Esperimenti, test, validazione di ipotesi, raccolta feedback

Genera 4-6 task fondamentali e complementari che:
- Coprano diverse fasi del progetto (Planning, Research, Design, Development, Testing, Marketing)
- Abbiano un mix bilanciato di tipi (almeno 1 proposal, 2-3 implementation, 1 validation)
- Evitino sovrapposizioni con task esistenti
- Abbiano equity rewards realistici e proporzionati

Per ogni task, fornisci:
1. **title**: Titolo chiaro e azionabile (max 80 caratteri)
2. **description**: Descrizione dettagliata con deliverable specifici (2-3 frasi)
3. **task_type**: 'proposal', 'implementation', o 'validation'
4. **phase**: Fase di sviluppo tra: Planning, Research, Design, Development, Testing, Marketing
5. **difficulty**: Tra Very Easy, Easy, Medium, Hard, Very Hard
6. **equity_reward**: Valore float tra 0.5 e 10.0 (proporzionato a difficoltà, importanza, tipo)
7. **hypothesis** (solo per validation): Ipotesi testabile formulata come "Crediamo che..."
8. **test_method** (solo per validation): Metodo concreto per testare l'ipotesi

Rispondi ESCLUSIVAMENTE in formato JSON valido con chiave "tasks" contenente array di task.{existing_context}
"""

    user_prompt = f'''Pitch: "{pitch}"
Categoria: "{category}"
Descrizione: "{description}"'''

    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=1200,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        response_content = chat_completion.choices[0].message.content
        parsed_response = json.loads(response_content)
        tasks = parsed_response.get('tasks', [])
        
        # Validazione e correzione dei task generati
        validated_tasks = []
        for task in tasks:
            # Assicurati che tutti i campi richiesti siano presenti
            if not all(key in task for key in ['title', 'description', 'task_type', 'phase', 'difficulty', 'equity_reward']):
                continue
            
            # Valida e correggi l'equity reward
            equity = task.get('equity_reward', 2.0)
            if isinstance(equity, str):
                try:
                    equity = float(equity)
                except ValueError:
                    equity = 2.0
            
            # Limita l'equity a range accettabile
            equity = max(0.5, min(10.0, equity))
            task['equity_reward'] = equity
            
            # Valida il task_type
            if task.get('task_type') not in ['proposal', 'implementation', 'validation']:
                task['task_type'] = 'implementation'
            
            # Aggiungi campi per validation se mancanti
            if task.get('task_type') == 'validation':
                if 'hypothesis' not in task or not task['hypothesis']:
                    task['hypothesis'] = f"Crediamo che {task['title'].lower()} sia una priorità per i nostri utenti target"
                if 'test_method' not in task or not task['test_method']:
                    task['test_method'] = "Creare un prototipo semplice e raccogliere feedback da 10-15 utenti potenziali"
            
            validated_tasks.append(task)
        
        return validated_tasks
        
    except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as api_err:
        current_app.logger.error(f"Errore API DeepSeek (tasks): {api_err}", exc_info=True)
        raise ConnectionError(f"Errore API DeepSeek: {api_err}")
    except json.JSONDecodeError as json_err:
        current_app.logger.error(f"Errore parsing JSON risposta AI (tasks): {json_err}", exc_info=True)
        return []  # Restituisce lista vuota in caso di errore parsing
    except Exception as e:
        current_app.logger.error(f"Errore imprevisto chiamata DeepSeek (tasks): {e}", exc_info=True)
        return []  # Restituisce lista vuota invece di sollevare eccezione

def generate_validation_experiment(project_pitch: str, project_category: str, project_description: str, focus_area: str = None) -> dict:
    """Genera un esperimento di validazione specifico per il progetto"""
    if not AI_SERVICE_AVAILABLE or client is None:
        return {"error": "AI Service not available"}

    system_prompt = """Sei un esperto in metodologia Lean Startup specializzato nella creazione di esperimenti di validazione.
Il tuo compito è creare un esperimento di validazione per testare un'ipotesi chiave del progetto.

Genera un esperimento di validazione che includa:
1.  **title**: Un titolo chiaro per l'esperimento.
2.  **description**: Una descrizione dell'esperimento e del suo obiettivo.
3.  **hypothesis**: Un'ipotesi specifica, misurabile e testabile (formulata come "Crediamo che...").
4.  **test_method**: Un metodo concreto, pratico e a basso costo per testare l'ipotesi.
5.  **success_criteria**: Criteri specifici per determinare se l'ipotesi è confermata o confutata.
6.  **estimated_duration**: Durata stimata dell'esperimento (es. "1 settimana", "2 settimane").
7.  **estimated_cost**: Costo stimato dell'esperimento (es. "50€", "100€", "Solo tempo").

L'esperimento deve essere:
- Realizzabile con risorse limitate
- Focalizzato su un'assunzione critica del business
- Misurabile con metriche concrete
- Completabile in massimo 2-3 settimane

Rispondi ESCLUSIVAMENTE in formato JSON valido."""
    
    focus_text = f"\nFocus specifico: {focus_area}" if focus_area else ""
    
    user_prompt = f'''Progetto: "{project_pitch}"
Categoria: "{project_category}"
Descrizione: "{project_description}"{focus_text}'''

    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=600,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content)
    except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as api_err:
        current_app.logger.error(f"Errore API DeepSeek (validation experiment): {api_err}", exc_info=True)
        raise ConnectionError(f"Errore API DeepSeek: {api_err}")
    except Exception as e:
        current_app.logger.error(f"Errore imprevisto chiamata DeepSeek (validation experiment): {e}", exc_info=True)
        raise Exception(f"Errore imprevisto generazione esperimento validazione: {e}")

def analyze_solution_content(task_title: str, task_description: str, solution_content: str) -> dict:
    if not AI_SERVICE_AVAILABLE or client is None:
        return {"error": "AI Service not available"}

    system_prompt = """Sei un esperto revisore di soluzioni per task di progetto.
Dati un titolo di task, una descrizione del task e il contenuto di una soluzione proposta, valuta la soluzione su due metriche:
1.  Coerenza: Quanto la soluzione è pertinente e allineata con i requisiti e gli obiettivi del task? (Punteggio da 0.0 a 1.0).
2.  Completezza: Quanto la soluzione sembra completa e indirizza tutti gli aspetti principali del task? (Punteggio da 0.0 a 1.0).
Fornisci una breve motivazione per ogni punteggio.
Rispondi ESCLUSIVAMENTE in formato JSON valido con le chiavi "coherence_score", "coherence_motivation", "completeness_score", "completeness_motivation".
"""
    user_prompt = f'''Titolo Task: "{task_title}"
Descrizione Task:
"""{task_description}"""

Contenuto Soluzione Proposta:
"""{solution_content}"""'''
    
    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=400,
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content)
    except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as api_err:
        current_app.logger.error(f"Errore API DeepSeek (analisi soluzione): {api_err}", exc_info=True)
        return {"error": f"Errore API DeepSeek: {api_err}"}
    except Exception as e:
        current_app.logger.error(f"Errore imprevisto chiamata DeepSeek (analisi soluzione): {e}", exc_info=True)
        return {"error": f"Errore imprevisto durante l'analisi AI della soluzione: {e}"}

def get_ai_contextual_help(context: str) -> str:
    """
    Fornisce aiuto contestuale personalizzato tramite AI per guidare gli utenti
    attraverso flussi di lavoro complessi in KICKStorm.
    """
    if not AI_SERVICE_AVAILABLE or client is None:
        return ""

    # Definizione dei prompt per contesti specifici
    context_prompts = {
        'github_workflow': {
            'system': """Sei un tutor esperto di GitHub e workflow di sviluppo open source. 
Il tuo compito è spiegare in modo chiaro e passo-passo come contribuire a un progetto software tramite GitHub.""",
            'user': """Spiegami come funziona il flusso di lavoro GitHub per contribuire a un progetto software:

1. Cosa significa "Fork" e come si fa
2. Come creare un "Branch" per il mio lavoro
3. Come aprire un "Pull Request"
4. Dove trovare l'URL del Pull Request per sottometterlo su KICKStorm

Usa un linguaggio semplice e fornisci esempi pratici. Massimo 300 parole."""
        },
        
        'hardware_submission': {
            'system': """Sei un tutor esperto di design hardware e prototipazione. 
Il tuo compito è guidare gli utenti nella sottomissione corretta di file di design hardware.""",
            'user': """Spiegami come sottomettere correttamente i file per un progetto hardware:

1. Che differenza c'è tra file "sorgente" e file "per prototipazione"
2. Quali formati usare (STEP vs STL, DWG vs GCODE)
3. Come documentare il mio lavoro per aumentare le possibilità di approvazione
4. Che tipo di prove visive includere

Usa un linguaggio tecnico ma accessibile. Massimo 350 parole."""
        },
        
        'task_creation': {
            'system': """Sei un esperto Project Manager specializzato nella creazione di task efficaci.""",
            'user': """Spiegami come creare un task ben strutturato su KICKStorm:

1. Come scegliere il tipo di task giusto (Proposta, Implementazione, Validazione)
2. Come definire un equity reward appropriato
3. Come scrivere una descrizione chiara e azionabile
4. Esempi di good practice per task diversi

Massimo 300 parole, linguaggio professionale ma chiaro."""
        },
        
        'project_collaboration': {
            'system': """Sei un esperto di collaborazione digitale e gestione progetti open source.""",
            'user': """Spiegami come collaborare efficacemente su un progetto KICKStorm:

1. Come funziona la Wiki del progetto
2. Come comunicare con altri collaboratori
3. Come seguire i progressi del progetto
4. Best practice per una collaborazione produttiva

Massimo 280 parole, tono amichevole e pratico."""
        },
        
        'solution_submission': {
            'system': """Sei un tutor esperto nell'aiutare gli utenti a sottomettere soluzioni di qualità.""",
            'user': """Spiegami come sottomettere una soluzione vincente:

1. Come strutturare la descrizione della soluzione
2. Cosa includere per dimostrare la qualità del lavoro
3. Come aumentare le possibilità di approvazione
4. Errori comuni da evitare

Massimo 320 parole, tono incoraggiante e pratico."""
        }
    }
    
    if context not in context_prompts:
        return "Contesto di aiuto non riconosciuto."
    
    prompt_config = context_prompts[context]
    
    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": prompt_config['system']},
                {"role": "user", "content": prompt_config['user']}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        response_content = chat_completion.choices[0].message.content.strip()
        return response_content
        
    except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as api_err:
        current_app.logger.error(f"Errore API DeepSeek (aiuto contestuale): {api_err}", exc_info=True)
        return "Servizio temporaneamente non disponibile. Riprova più tardi."
    except Exception as e:
        current_app.logger.error(f"Errore imprevisto chiamata DeepSeek (aiuto contestuale): {e}", exc_info=True)
        return "Si è verificato un errore. Riprova più tardi."

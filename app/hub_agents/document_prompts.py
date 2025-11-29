# app/hub_agents/document_prompts.py
"""
Prompt specifici per ogni tipo di documento dell'Hub Agents.
Ogni documento ha il suo prompt specializzato per generare contenuti di qualità.
"""

DOCUMENT_PROMPTS = {
    # ========== 00_IDEA_VALIDATION ==========
    "problem_definition.md": """Sei un esperto di Product Discovery e Customer Development.
Il tuo compito è definire chiaramente il problema che il progetto intende risolvere.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Descrizione: {description}
- Categoria: {category}
- Tipo: {project_type}

ISTRUZIONI:
1. Analizza il pitch e la descrizione per identificare il problema principale
2. Definisci chi è affetto da questo problema (target audience)
3. Spiega perché questo problema è importante e urgente
4. Descrivi le conseguenze del problema non risolto
5. Identifica i pain points specifici

FORMATO RISPOSTA (Markdown):
# Problem Definition

## Il Problema
[Descrizione chiara e concisa del problema principale]

## Chi è Affetto
[Descrizione del target audience e delle persone che soffrono di questo problema]

## Perché è Importante
[Spiegazione dell'urgenza e dell'impatto del problema]

## Pain Points Specifici
1. [Pain point 1]
2. [Pain point 2]
3. [Pain point 3]

## Conseguenze del Problema Non Risolto
[Descrizione di cosa succede se il problema non viene risolto]""",

    "solution_hypothesis.md": """Sei un esperto di Lean Startup e Validated Learning.
Il tuo compito è formulare ipotesi chiare sulla soluzione proposta.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Descrizione: {description}
- Categoria: {category}
- Tipo: {project_type}

ISTRUZIONI:
1. Basandoti sul problema identificato, formula l'ipotesi di soluzione
2. Descrivi come la soluzione risolve il problema
3. Identifica le assunzioni chiave da validare
4. Proponi esperimenti per testare le ipotesi

FORMATO RISPOSTA (Markdown):
# Solution Hypothesis

## Ipotesi di Soluzione
[Descrizione chiara di come il progetto risolve il problema]

## Come Risolve il Problema
[Spiegazione dettagliata del meccanismo di risoluzione]

## Assunzioni Chiave da Validare
1. [Assunzione 1 - es: "Gli utenti sono disposti a pagare X per questa soluzione"]
2. [Assunzione 2]
3. [Assunzione 3]

## Esperimenti Proposti
[Descrizione di come validare ogni assunzione]""",

    "target_audience_personas.md": """Sei un esperto di Marketing e User Research.
Il tuo compito è creare personas dettagliate del target audience.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Descrizione: {description}
- Categoria: {category}
- Tipo: {project_type}

ISTRUZIONI:
1. Identifica 2-3 personas principali
2. Per ogni persona, descrivi: demografia, comportamenti, bisogni, obiettivi, frustrazioni
3. Identifica quale persona è il "early adopter" ideale

FORMATO RISPOSTA (Markdown):
# Target Audience Personas

## Persona 1: [Nome]
- **Età**: [range]
- **Professione**: [tipo]
- **Bisogni**: [lista]
- **Obiettivi**: [cosa vuole raggiungere]
- **Frustrazioni**: [cosa lo infastidisce]
- **Comportamenti**: [come si comporta]

## Persona 2: [Nome]
[stesso formato]

## Early Adopter Ideale
[Descrizione di quale persona è più probabile adottare per prima la soluzione]""",

    "customer_interviews_template.md": """Sei un esperto di Customer Development e User Research.
Crea un template per interviste con i clienti.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Descrizione: {description}
- Categoria: {category}

ISTRUZIONI:
Crea un template di domande per intervistare potenziali clienti e validare il problema e la soluzione.

FORMATO RISPOSTA (Markdown):
# Customer Interviews Template

## Domande sul Problema
1. [Domanda per capire il problema]
2. [Domanda per capire la frequenza]
3. [Domanda per capire l'urgenza]

## Domande sulla Soluzione
1. [Domanda per validare l'interesse]
2. [Domanda per capire il valore percepito]
3. [Domanda sul pricing]

## Domande Demografiche
[Domande per segmentare gli intervistati]""",

    "survey_questions.md": """Sei un esperto di Market Research.
Crea un questionario per validare il problema e la soluzione.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Crea 10-15 domande per un survey online che validi il problema e l'interesse per la soluzione.

FORMATO RISPOSTA (Markdown):
# Survey Questions

## Sezione 1: Demografia
[Domande demografiche]

## Sezione 2: Il Problema
[Domande sul problema]

## Sezione 3: La Soluzione
[Domande sulla soluzione proposta]

## Sezione 4: Pricing e Willingness to Pay
[Domande sul prezzo]""",

    "validation_metrics.md": """Sei un esperto di Product Metrics e Analytics.
Definisci le metriche per validare il progetto.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Definisci metriche specifiche per validare problema, soluzione e modello di business.

FORMATO RISPOSTA (Markdown):
# Validation Metrics

## Metriche di Problema
- [Metrica 1]: [Come misurarla]
- [Metrica 2]: [Come misurarla]

## Metriche di Soluzione
- [Metrica 1]: [Come misurarla]
- [Metrica 2]: [Come misurarla]

## Metriche di Business Model
- [Metrica 1]: [Come misurarla]
- [Metrica 2]: [Come misurarla]""",

    "pivot_decision_framework.md": """Sei un esperto di Lean Startup.
Crea un framework per decidere quando fare pivot.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}

ISTRUZIONI:
Crea un framework decisionale per capire quando fare pivot vs perseverare.

FORMATO RISPOSTA (Markdown):
# Pivot Decision Framework

## Segnali per Fare Pivot
[Lista di segnali che indicano la necessità di pivot]

## Segnali per Perseverare
[Lista di segnali positivi]

## Processo Decisionale
[Step-by-step per prendere la decisione]""",

    # ========== 01_MARKET_RESEARCH ==========
    "market_size_analysis.md": """Sei un esperto di Market Research e Business Analysis.
Analizza la dimensione del mercato per il progetto.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Calcola TAM, SAM, SOM e fornisci analisi del mercato.

FORMATO RISPOSTA (Markdown):
# Market Size Analysis

## TAM (Total Addressable Market)
[Stima del mercato totale]

## SAM (Serviceable Available Market)
[Stima del mercato raggiungibile]

## SOM (Serviceable Obtainable Market)
[Stima del mercato ottenibile nei primi anni]

## Metodologia
[Come sono state calcolate le stime]""",

    "competitor_matrix.md": """Sei un esperto di Competitive Analysis.
Crea una matrice dei competitor.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Identifica i competitor principali e confrontali su diverse dimensioni.

FORMATO RISPOSTA (Markdown):
# Competitor Matrix

## Competitor Diretti
[Tabella con confronto su: prezzo, features, target, punti di forza/debolezza]

## Competitor Indiretti
[Alternative che risolvono lo stesso problema in modo diverso]

## Posizionamento Competitivo
[Dove si posiziona questo progetto rispetto ai competitor]""",

    # ========== 02_BUSINESS_MODEL ==========
    "lean_canvas.md": """Sei un esperto di Business Model Design e Lean Canvas.
Il tuo compito è compilare un Lean Canvas completo per il progetto.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Descrizione: {description}
- Categoria: {category}
- Tipo: {project_type}

ISTRUZIONI:
Compila tutte le sezioni del Lean Canvas:
1. Problema (top 3 problemi)
2. Soluzione (top 3 features)
3. Metriche Chiave
4. Value Proposition
5. Vantaggio Competitivo
6. Canali
7. Segmenti di Clienti
8. Struttura Costi
9. Flussi di Ricavi

FORMATO RISPOSTA (Markdown):
# Lean Canvas: {name}

## Problema
1. [Problema principale 1]
2. [Problema principale 2]
3. [Problema principale 3]

## Soluzione
1. [Feature/Soluzione 1]
2. [Feature/Soluzione 2]
3. [Feature/Soluzione 3]

## Metriche Chiave
[KPIs principali da tracciare]

## Value Proposition
[Proposta di valore unica in 1-2 frasi]

## Vantaggio Competitivo
[Cosa rende questa soluzione difficile da copiare]

## Canali
[Come raggiungere i clienti]

## Segmenti di Clienti
[Chi sono i clienti target]

## Struttura Costi
[Costi principali operativi]

## Flussi di Ricavi
[Come il progetto genera ricavi]""",

    "business_model_canvas.md": """Sei un esperto di Business Model Innovation.
Il tuo compito è creare un Business Model Canvas completo.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Descrizione: {description}
- Categoria: {category}
- Tipo: {project_type}

ISTRUZIONI:
Compila tutte le 9 sezioni del Business Model Canvas.

FORMATO RISPOSTA (Markdown):
# Business Model Canvas: {name}

## Partner Chiave
[Lista dei partner strategici necessari]

## Attività Chiave
[Attività principali per far funzionare il business]

## Risorse Chiave
[Risorse necessarie: umane, finanziarie, tecnologiche, fisiche]

## Value Propositions
[Proposta di valore per ogni segmento di clienti]

## Relazioni con i Clienti
[Tipo di relazione che si vuole stabilire]

## Canali
[Canali per raggiungere e servire i clienti]

## Segmenti di Clienti
[Segmenti di clienti target]

## Struttura dei Costi
[Costi principali del modello di business]

## Flussi di Ricavi
[Fonti di ricavo e meccanismi di pricing]""",

    "value_proposition_canvas.md": """Sei un esperto di Value Proposition Design.
Crea un Value Proposition Canvas dettagliato.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Compila il Value Proposition Canvas con customer jobs, pains, gains e come la soluzione li soddisfa.

FORMATO RISPOSTA (Markdown):
# Value Proposition Canvas: {name}

## Customer Jobs
[Cosa il cliente sta cercando di fare]

## Customer Pains
[Problemi e frustrazioni del cliente]

## Customer Gains
[Benefici che il cliente cerca]

## Products & Services
[Come la soluzione soddisfa jobs, allevia pains, crea gains]""",

    "revenue_streams.md": """Sei un esperto di Business Model e Revenue Strategy.
Definisci i flussi di ricavo per il progetto.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Identifica e descrivi tutti i possibili flussi di ricavo.

FORMATO RISPOSTA (Markdown):
# Revenue Streams: {name}

## Flusso di Ricavo 1: [Nome]
- Tipo: [Subscription/Transaction/Advertising/etc]
- Descrizione: [Come funziona]
- Pricing: [Modello di prezzo]
- Stima: [Proiezione]

## Flusso di Ricavo 2: [Nome]
[stesso formato]""",

    "cost_structure.md": """Sei un esperto di Financial Planning.
Definisci la struttura dei costi per il progetto.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Categoria: {category}

ISTRUZIONI:
Identifica tutti i costi principali (fissi e variabili).

FORMATO RISPOSTA (Markdown):
# Cost Structure: {name}

## Costi Fissi
- [Costo 1]: [Importo mensile/annuale]
- [Costo 2]: [Importo]

## Costi Variabili
- [Costo 1]: [Per unità/transazione]
- [Costo 2]: [Per unità]

## Break-Even Analysis
[Calcolo del punto di pareggio]""",

    "unit_economics.md": """Sei un esperto di Unit Economics e Financial Modeling.
Calcola le unit economics per il progetto.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Categoria: {category}

ISTRUZIONI:
Calcola CAC, LTV, LTV:CAC ratio, payback period.

FORMATO RISPOSTA (Markdown):
# Unit Economics: {name}

## Customer Acquisition Cost (CAC)
[Calcolo e spiegazione]

## Lifetime Value (LTV)
[Calcolo e spiegazione]

## LTV:CAC Ratio
[Calcolo e interpretazione]

## Payback Period
[Tempo per recuperare il CAC]

## Margine per Cliente
[Calcolo del margine]""",

    "financial_projections.md": """Sei un esperto di Financial Planning e Forecasting.
Crea proiezioni finanziarie per i primi 3 anni.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Categoria: {category}

ISTRUZIONI:
Crea proiezioni realistiche di ricavi, costi, utenti per 3 anni.

FORMATO RISPOSTA (Markdown):
# Financial Projections: {name}

## Anno 1
- Ricavi: [stima]
- Costi: [stima]
- Utenti: [stima]
- EBITDA: [stima]

## Anno 2
[stesso formato]

## Anno 3
[stesso formato]

## Assunzioni Chiave
[Lista delle assunzioni principali]""",

    # ========== 03_PRODUCT_STRATEGY ==========
    "mvp_definition.md": """Sei un esperto Product Manager specializzato in MVP (Minimum Viable Product).
Il tuo compito è definire un MVP chiaro e realizzabile.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Descrizione: {description}
- Categoria: {category}
- Tipo: {project_type}
{ai_mvp_guide_context}

ISTRUZIONI:
1. Identifica le funzionalità CORE assolute (must-have)
2. Definisci cosa NON includere nell'MVP (nice-to-have per dopo)
3. Crea una roadmap di sviluppo in fasi
4. Suggerisci stack tecnologico appropriato
5. Stima tempi realistici
6. Definisci metriche di successo

FORMATO RISPOSTA (Markdown):
# MVP Definition: {name}

## Obiettivo MVP
[Descrizione chiara di cosa deve fare l'MVP in 2-3 frasi]

## Funzionalità Core (Must-Have)
1. **[Funzionalità 1]**: [Descrizione breve]
2. **[Funzionalità 2]**: [Descrizione breve]
3. **[Funzionalità 3]**: [Descrizione breve]

## Funzionalità Escluse dall'MVP
[Funzionalità che verranno aggiunte in versioni successive]

## Roadmap di Sviluppo

### Fase 1: Fondamenta (Settimana 1-2)
- [ ] [Task specifico]
- [ ] [Task specifico]

### Fase 2: Funzionalità Core (Settimana 3-4)
- [ ] [Task specifico]
- [ ] [Task specifico]

### Fase 3: Testing e Rilascio (Settimana 5-6)
- [ ] [Task specifico]
- [ ] [Task specifico]

## Stack Tecnologico Consigliato
- **Frontend**: [Raccomandazione]
- **Backend**: [Raccomandazione]
- **Database**: [Raccomandazione]
- **Hosting**: [Raccomandazione]

## Metriche di Successo
1. [Metrica misurabile]
2. [Metrica misurabile]""",

    "feature_prioritization_matrix.md": """Sei un esperto di Product Prioritization.
Crea una matrice di prioritizzazione delle feature.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Usa una matrice Value vs Effort per prioritizzare le feature.

FORMATO RISPOSTA (Markdown):
# Feature Prioritization Matrix: {name}

## Quick Wins (Alto Valore, Basso Sforzo)
- [Feature 1]
- [Feature 2]

## Major Projects (Alto Valore, Alto Sforzo)
- [Feature 1]
- [Feature 2]

## Fill-ins (Basso Valore, Basso Sforzo)
- [Feature 1]

## Time Sinks (Basso Valore, Alto Sforzo)
- [Feature da evitare]""",

    "user_stories.md": """Sei un esperto di Agile e User Stories.
Scrivi user stories per le funzionalità principali.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Scrivi user stories nel formato: "Come [persona], voglio [azione] così che [beneficio]".

FORMATO RISPOSTA (Markdown):
# User Stories: {name}

## Epic 1: [Nome Epic]

### Story 1.1
**Come** [persona] **voglio** [azione] **così che** [beneficio]

**Criteri di Accettazione:**
- [Criterio 1]
- [Criterio 2]

### Story 1.2
[stesso formato]""",

    "product_roadmap.md": """Sei un esperto di Product Roadmapping.
Crea una roadmap di prodotto per 12 mesi.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Organizza le feature in trimestri con obiettivi chiari.

FORMATO RISPOSTA (Markdown):
# Product Roadmap: {name}

## Q1: [Obiettivo Trimestre]
- [Feature/Milestone 1]
- [Feature/Milestone 2]

## Q2: [Obiettivo Trimestre]
- [Feature/Milestone 1]
- [Feature/Milestone 2]

## Q3: [Obiettivo Trimestre]
[stesso formato]

## Q4: [Obiettivo Trimestre]
[stesso formato]""",

    "tech_stack_recommendations.md": """Sei un esperto di Software Architecture e Technology Selection.
Raccomanda lo stack tecnologico per il progetto.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Raccomanda stack tecnologico considerando: costo, scalabilità, velocità di sviluppo, community.

FORMATO RISPOSTA (Markdown):
# Tech Stack Recommendations: {name}

## Frontend
- **Framework**: [Raccomandazione e perché]
- **Librerie**: [Lista]

## Backend
- **Framework/Language**: [Raccomandazione e perché]
- **API**: [Raccomandazione]

## Database
- **Primario**: [Raccomandazione]
- **Cache**: [Raccomandazione se necessario]

## Hosting & Infrastructure
- **Hosting**: [Raccomandazione]
- **CDN**: [Raccomandazione se necessario]

## Considerazioni
[Trade-offs e ragioni delle scelte]""",

    # ========== 04_GO_TO_MARKET ==========
    "gtm_strategy.md": """Sei un esperto di Go-to-Market Strategy.
Crea una strategia GTM completa.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Categoria: {category}

ISTRUZIONI:
Definisci strategia di lancio, canali, messaggi, timeline.

FORMATO RISPOSTA (Markdown):
# Go-to-Market Strategy: {name}

## Obiettivi GTM
[Obiettivi principali del lancio]

## Target Audience
[Descrizione del target per il lancio]

## Messaggi Chiave
[3-5 messaggi principali da comunicare]

## Canali di Lancio
[Canali principali e secondari]

## Timeline
[Timeline del lancio con milestone]""",

    "pricing_strategy.md": """Sei un esperto di Pricing Strategy.
Definisci la strategia di pricing.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Categoria: {category}

ISTRUZIONI:
Definisci modello di pricing, tier, strategia.

FORMATO RISPOSTA (Markdown):
# Pricing Strategy: {name}

## Modello di Pricing
[Subscription/One-time/Freemium/etc]

## Tier di Prezzo
- **Tier 1**: [Nome] - €[prezzo]/[periodo]
  - [Feature incluse]
- **Tier 2**: [Nome] - €[prezzo]/[periodo]
  - [Feature incluse]

## Strategia
[Spiegazione della strategia di pricing]""",

    # ========== 06_FUNDRAISING ==========
    "pitch_deck.md": """Sei un esperto di Pitch Deck e Fundraising.
Crea una struttura di pitch deck per investitori.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Descrizione: {description}
- Categoria: {category}

ISTRUZIONI:
Crea una struttura di 10-12 slide per un pitch deck professionale.

FORMATO RISPOSTA (Markdown):
# Pitch Deck Structure: {name}

## Slide 1: Title Slide
[Contenuto suggerito]

## Slide 2: Problem
[Contenuto suggerito]

## Slide 3: Solution
[Contenuto suggerito]

## Slide 4: Market Opportunity
[Contenuto suggerito]

## Slide 5: Business Model
[Contenuto suggerito]

## Slide 6: Traction
[Contenuto suggerito]

## Slide 7: Competition
[Contenuto suggerito]

## Slide 8: Team
[Contenuto suggerito]

## Slide 9: Financials
[Contenuto suggerito]

## Slide 10: Ask
[Contenuto suggerito]""",

    "elevator_pitch.md": """Sei un esperto di Communication e Storytelling.
Crea un elevator pitch efficace.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Descrizione: {description}

ISTRUZIONI:
Crea 3 versioni: 30 secondi, 1 minuto, 2 minuti.

FORMATO RISPOSTA (Markdown):
# Elevator Pitch: {name}

## Versione 30 Secondi
[Pitch breve e incisivo]

## Versione 1 Minuto
[Pitch con più dettagli]

## Versione 2 Minuti
[Pitch completo con esempi]""",
}

def get_document_prompt(doc_type: str) -> str:
    """
    Restituisce il prompt specifico per un tipo di documento.
    Se non esiste un prompt specifico, restituisce un prompt generico.
    """
    # Estrai solo il nome del file senza path
    filename = doc_type.split('/')[-1] if '/' in doc_type else doc_type
    
    return DOCUMENT_PROMPTS.get(filename, None)

def get_default_prompt(doc_type: str) -> str:
    """
    Restituisce un prompt generico di fallback se non esiste un prompt specifico.
    """
    return """Sei un esperto product manager e startup advisor.
Il tuo compito è generare contenuto professionale per il documento '{doc_type}'.

INFORMAZIONI PROGETTO:
- Nome: {name}
- Pitch: {pitch}
- Descrizione: {description}
- Categoria: {category}
- Tipo: {project_type}

ISTRUZIONI:
Genera un contenuto dettagliato, strutturato in Markdown, professionale e pronto all'uso.
Il contenuto deve essere specifico per questo tipo di documento e pertinente al progetto.
Non includere saluti o testo introduttivo, solo il contenuto del documento."""


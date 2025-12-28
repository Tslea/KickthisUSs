# 🤖 Wiki to Tasks - Feature Documentation

## 📋 Overview

Questa feature permette di **generare automaticamente task actionable** dal contenuto di una pagina Wiki del progetto.

È perfetta per trasformare:
- ✅ Checklist di implementazione
- ✅ Roadmap di sviluppo
- ✅ Analisi di gap tecnico
- ✅ Liste di funzionalità mancanti
- ✅ Production-ready checklist

...in **task concreti** che possono essere assegnati e completati dal team.

---

## 🎯 Come Funziona

### 1. **Scrivi/Incolla Analisi nella Wiki**
Crea una pagina wiki nel tuo progetto e incolla:
- Analisi production-ready (es. "cosa manca per MVP")
- Checklist di task da fare
- Roadmap con priorità
- Qualsiasi documento strutturato con azioni concrete

**Esempio di contenuto wiki:**
```markdown
## 🔴 CRITICI - Devono essere implementati

### 1. Database PostgreSQL Setup
- [ ] Setup PostgreSQL su Neon (GRATIS)
- [ ] Migrazione dati SQLite → PostgreSQL
- [ ] Backup strategy configurata

### 2. Rate Limiting
- [ ] Implementare Flask-Limiter
- [ ] Proteggere endpoint login (5 req/min)
- [ ] Proteggere API (100 req/hour)

## 🟡 IMPORTANTI

### 3. GDPR Compliance
- [ ] Cookie banner (Cookieconsent.js)
- [ ] Privacy Policy page
- [ ] Data export feature
```

### 2. **Clicca "🤖 Genera Task"**
Nella pagina wiki, troverai il pulsante **"🤖 Genera Task"** in alto a destra.

### 3. **AI Analizza il Contenuto**
L'AI DeepSeek:
- 📖 Legge il contenuto della pagina wiki
- 🎯 Estrae task actionable e concreti
- 📊 Assegna priorità, difficoltà ed equity
- 🔄 Evita duplicati con task esistenti
- ✅ Crea task con stato `suggested` (da approvare)

### 4. **Approva i Task**
I task generati vengono creati con:
- ✅ **Status**: `suggested` (suggerito dall'AI)
- ✅ **Flag**: `is_suggestion=True`

Il **creator del progetto** può poi:
1. **Approvarli** (cambiano status da `suggested` → `open`)
2. **Rifiutarli** (eliminarli)
3. **Renderli privati** (visibili solo a creator/collaboratori)
4. **Renderli pubblici** (visibili a tutti)

---

## 🔧 Implementazione Tecnica

### File Modificati/Creati

#### 1. `app/ai_services.py`
**Nuova funzione aggiunta:**
```python
def generate_tasks_from_wiki_analysis(
    wiki_content: str,
    project_pitch: str,
    project_description: str,
    project_category: str,
    existing_tasks: list = None
) -> list
```

**Cosa fa:**
- Analizza contenuto wiki con DeepSeek AI
- Estrae task actionable con stessa struttura di `generate_suggested_tasks()`
- Valida campi (title, description, task_type, phase, difficulty, equity_reward)
- Aggiunge campi `hypothesis` e `test_method` per task di tipo `validation`
- Restituisce lista di task dict

**Non modifica nessuna funzionalità esistente** ✅

---

#### 2. `app/api_ai_wiki.py`
**Nuovo endpoint aggiunto:**
```python
@api_ai_wiki.route('/wiki/<int:project_id>/page/<slug>/generate-tasks', methods=['POST'])
@login_required
def generate_tasks_from_wiki(project_id, slug)
```

**Cosa fa:**
- Verifica permessi (solo creator e collaboratori)
- Valida contenuto minimo (100 caratteri)
- Chiama `generate_tasks_from_wiki_analysis()`
- Crea task nel database con `status='suggested'` e `is_suggestion=True`
- Gestisce task `validation` con campi specifici
- Restituisce JSON con task creati

**Usa la stessa logica di `suggest_ai_task_api()` in `routes_tasks.py`** ✅

---

#### 3. `app/templates/wiki/view_page.html`
**Modifiche:**
1. **Nuovo pulsante** in header (accanto a "Modifica", "Cronologia")
2. **Modal** per mostrare:
   - Loading state durante generazione
   - Success state con lista task generati
   - Error state in caso di problemi
3. **JavaScript** per:
   - Aprire/chiudere modal
   - Chiamata AJAX a `/api/ai-wiki/wiki/<project_id>/page/<slug>/generate-tasks`
   - Display task con emoji, difficoltà, equity, phase

**Non modifica nessun altro elemento della pagina** ✅

---

## 📊 Flusso Completo

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User crea pagina Wiki con analisi/checklist                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. User clicca "🤖 Genera Task" nella pagina Wiki              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Frontend invia POST a /api/ai-wiki/wiki/:id/page/:slug/     │
│    generate-tasks                                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Backend chiama generate_tasks_from_wiki_analysis()          │
│    - Analizza contenuto wiki con DeepSeek AI                   │
│    - Estrae task actionable                                    │
│    - Evita duplicati con task esistenti                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Backend crea task nel database:                             │
│    - status = 'suggested'                                       │
│    - is_suggestion = True                                       │
│    - creator_id = current_user.id                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Frontend mostra modal con task generati                     │
│    - Link per andare alla pagina progetto                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Creator va alla pagina progetto e:                          │
│    ✅ Approva task (status: suggested → open)                  │
│    ❌ Rifiuta task (elimina)                                   │
│    🔒 Rende task privato (is_private = True)                   │
│    🌍 Rende task pubblico (is_private = False)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎨 UI/UX

### Pulsante "🤖 Genera Task"
- **Posizione**: Header pagina wiki, accanto a "Modifica"
- **Stile**: Gradient viola-indigo con icona
- **Hover**: Shadow e transizione smooth
- **Solo visibile a**: Creator e collaboratori

### Modal di Generazione
**Stati:**
1. **Loading**: Spinner + messaggio "Analisi in corso..."
2. **Success**: 
   - ✅ Badge verde "Task generati con successo"
   - Lista task con emoji, titolo, descrizione, badge (difficulty, phase, type)
   - Nota: "I task sono in stato 'suggested', vai al progetto per approvarli"
   - Pulsanti: "Chiudi" + "Vai al Progetto →"
3. **Error**: 
   - ❌ Badge rosso con messaggio errore
   - Pulsante "Chiudi"

---

## 🔒 Sicurezza e Permessi

### Chi può generare task?
- ✅ **Creator del progetto**
- ✅ **Collaboratori del progetto**
- ❌ **Visitatori esterni**

### Validazioni
- ✅ Autenticazione richiesta (`@login_required`)
- ✅ Check permessi via `check_wiki_edit_permission()`
- ✅ Contenuto minimo: 100 caratteri
- ✅ CSRF token protection
- ✅ Rate limiting (eredita da config Flask-Limiter)

---

## 🧪 Testing

### Test Manuale
1. Crea un progetto
2. Vai alla Wiki del progetto
3. Crea pagina "Production Roadmap"
4. Incolla questa analisi:
   ```markdown
   ## CRITICI
   - [ ] Setup PostgreSQL database
   - [ ] Implementare rate limiting
   - [ ] Aggiungere HTTPS/SSL
   
   ## IMPORTANTI
   - [ ] Cookie banner GDPR
   - [ ] Privacy policy page
   ```
5. Clicca "🤖 Genera Task"
6. Verifica modal con task generati
7. Vai al progetto → verifica task con badge "SUGGESTED"

### Test Casi Edge
- ✅ Pagina wiki vuota → Errore "contenuto troppo breve"
- ✅ Non autenticato → Redirect a login
- ✅ Non collaboratore → Errore 403
- ✅ Errore AI → Modal mostra errore friendly
- ✅ Task duplicati → AI li evita (context `existing_tasks`)

---

## 📈 Metriche e Monitoraggio

### Log Events
```python
# Success
logger.info(f"Generati {len(created_tasks)} task da pagina wiki '{wiki_page.title}' per progetto {project.id}")

# Errori
logger.error(f"Errore connessione AI durante generazione task da wiki: {str(conn_err)}")
logger.error(f"Errore generazione task da wiki: {str(e)}", exc_info=True)
```

### Metriche da tracciare
- Numero task generati per pagina wiki
- Tasso di approvazione task (suggested → open)
- Progetti che usano la feature
- Errori API DeepSeek

---

## 🚀 Utilizzo Pratico

### Use Case 1: Dogfooding KickStorm
**Scenario:** Sviluppare KickStorm usando KickStorm
```markdown
1. Crea progetto "KickStorm Development"
2. Crea wiki page "MVP Production Checklist"
3. Incolla analisi (come quella che ti ho fatto)
4. Clicca "🤖 Genera Task"
5. Approva task prioritari
6. Assegna a collaboratori
7. Traccia progresso
```

### Use Case 2: Analisi Post-Review
**Scenario:** Dopo code review, crei checklist miglioramenti
```markdown
1. Code review identifica 10 issue
2. Crei wiki "Code Quality Improvements"
3. Incolli lista issue
4. Genera task automaticamente
5. Ogni issue diventa un task assegnabile
```

### Use Case 3: Roadmap Trimestrale
**Scenario:** Planning Q1 2025
```markdown
1. Crei wiki "Q1 2025 Roadmap"
2. Incolli priorità e milestone
3. Genera task per ogni milestone
4. Team può iniziare a lavorare subito
```

---

## 🛠️ Troubleshooting

### Problema: "Contenuto troppo breve"
**Soluzione:** Aggiungi più dettagli alla pagina wiki (minimo 100 caratteri)

### Problema: "Errore API DeepSeek"
**Cause possibili:**
- OPENAI_API_KEY non configurata
- Rate limit DeepSeek raggiunto
- Timeout di rete

**Soluzione:**
- Verifica `.env` abbia `OPENAI_API_KEY`
- Attendi qualche secondo e riprova
- Check logs: `logs/app.log`

### Problema: "Task duplicati generati"
**Non dovrebbe succedere:** L'AI riceve lista task esistenti
**Se succede:** Report bug con contenuto wiki e task esistenti

### Problema: "Task non approvabili"
**Verifica:**
- Task ha `status='suggested'`
- Task ha `is_suggestion=True`
- Sei creator o collaboratore del progetto

---

## 🔄 Compatibilità

### Con funzionalità esistenti
- ✅ **"Suggerisci Task con AI"**: Funziona indipendentemente, stessa logica di approvazione
- ✅ **Task privati**: Task generati possono essere resi privati dopo approvazione
- ✅ **Equity system**: Task generati hanno equity_reward assegnato dall'AI
- ✅ **Task validation**: Task di tipo `validation` hanno campi `hypothesis` e `test_method`
- ✅ **Collaboratori**: Solo creator/collaboratori possono generare task

### Backward compatibility
- ✅ **Nessuna migration database richiesta**
- ✅ **Nessuna modifica a funzioni esistenti**
- ✅ **Solo aggiunta di nuove funzioni**
- ✅ **Progetti esistenti funzionano senza cambiamenti**

---

## 📚 API Reference

### Endpoint: Generate Tasks from Wiki

**URL:** `POST /api/ai-wiki/wiki/<project_id>/page/<slug>/generate-tasks`

**Headers:**
```http
Content-Type: application/json
X-CSRFToken: <csrf_token>
```

**Authentication:** Required (`@login_required`)

**Permissions:** Creator or Collaborator of project

**Response Success (200):**
```json
{
  "success": true,
  "message": "4 task generati con successo dalla pagina wiki",
  "tasks_created": 4,
  "wiki_page_title": "Production Roadmap",
  "tasks": [
    {
      "title": "Setup PostgreSQL database su Neon",
      "description": "Configurare database PostgreSQL gratuito...",
      "task_type": "implementation",
      "phase": "Development",
      "difficulty": "Medium",
      "equity_reward": 4.5
    }
  ]
}
```

**Response Error (400):**
```json
{
  "success": false,
  "error": "Il contenuto della pagina è troppo breve per generare task (minimo 100 caratteri)"
}
```

**Response Error (403):**
```json
{
  "success": false,
  "error": "Non hai i permessi per generare task per questo progetto"
}
```

**Response Error (500):**
```json
{
  "success": false,
  "error": "Non è stato possibile generare task dal contenuto della pagina. Riprova o modifica il contenuto."
}
```

---

## 🎓 Best Practices

### Scrittura Contenuto Wiki Ottimale

**✅ DO:**
- Usa checklist markdown (`- [ ]`)
- Dividi per priorità (Critico, Importante, Opzionale)
- Includi dettagli tecnici specifici
- Usa headers (`##`, `###`) per struttura
- Spiega deliverable concreti

**❌ DON'T:**
- Task troppo generici ("Migliorare performance")
- Contenuto troppo breve (<100 caratteri)
- Solo testo narrativo senza struttura
- Link esterni senza spiegazione

**Esempio OTTIMO:**
```markdown
## 🔴 CRITICO

### 1. Database PostgreSQL Setup
**Obiettivo:** Migrare da SQLite a PostgreSQL produzione
**Deliverable:**
- [ ] Setup database su Neon.tech (gratuito)
- [ ] Migrazione schema con Flask-Migrate
- [ ] Test connessione e query
- [ ] Backup automatico configurato
**Equity stimata:** 5-6%

### 2. Rate Limiting Implementation
**Obiettivo:** Proteggere API da abuse
**Deliverable:**
- [ ] Installare Flask-Limiter
- [ ] Configurare 5 req/min su /login
- [ ] Configurare 100 req/hour su API
- [ ] Test con tool di load testing
**Equity stimata:** 3-4%
```

---

## 🎉 Conclusione

Questa feature ti permette di:
1. ✅ **Velocizzare planning** trasformando analisi in task
2. ✅ **Evitare lavoro manuale** di creazione task uno ad uno
3. ✅ **Mantenere controllo** con sistema approvazione
4. ✅ **Usare KickStorm per sviluppare KickStorm** (dogfooding)

**Ready to use!** 🚀

---

## 📞 Support

Per problemi o domande:
- 📝 Crea issue su GitHub
- 📧 Email support
- 💬 Discord community

**Version:** 1.0.0
**Last Updated:** October 22, 2025

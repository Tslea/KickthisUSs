# 🧪 Quick Test - Wiki to Tasks Feature

## Test Rapido Funzionalità

### Pre-requisiti
- [x] App Flask avviata
- [x] Utente loggato
- [x] Progetto creato
- [x] OPENAI_API_KEY configurata in `.env`

---

## Test 1: Generazione Task da Wiki ✅

### Steps:
1. **Vai al tuo progetto**
   ```
   http://localhost:5000/project/<project_id>
   ```

2. **Vai alla Wiki**
   - Clicca tab "Wiki"

3. **Crea nuova pagina**
   - Titolo: "MVP Production Checklist"
   - Slug: `mvp-production-checklist`

4. **Incolla questo contenuto:**
   ```markdown
   ## 🔴 CRITICI - Devono essere implementati

   ### 1. Database PostgreSQL Setup
   - [ ] Creare database PostgreSQL su Neon.tech (gratuito)
   - [ ] Migrare schema da SQLite con Flask-Migrate
   - [ ] Configurare connection pooling
   - [ ] Setup backup automatici giornalieri
   - [ ] Test performance query

   ### 2. Rate Limiting con Flask-Limiter
   - [ ] Installare Flask-Limiter package
   - [ ] Configurare storage Redis o Memory
   - [ ] Implementare 5 req/min su endpoint /login
   - [ ] Implementare 100 req/hour su API endpoints
   - [ ] Test con load testing tool (Locust/JMeter)

   ### 3. HTTPS/SSL Certificate
   - [ ] Configurare Let's Encrypt su server
   - [ ] Redirect HTTP → HTTPS automatico
   - [ ] Test SSL Labs rating (target: A+)
   - [ ] Setup auto-renewal certificato

   ## 🟡 IMPORTANTI - Fortemente raccomandati

   ### 4. GDPR Cookie Compliance
   - [ ] Implementare cookie banner con Cookieconsent.js
   - [ ] Creare pagina Privacy Policy
   - [ ] Creare pagina Terms of Service
   - [ ] Implementare data export feature per utenti
   - [ ] Implementare account deletion feature

   ### 5. Error Monitoring con Sentry
   - [ ] Setup account Sentry.io (free tier)
   - [ ] Installare sentry-sdk[flask]
   - [ ] Configurare DSN in environment variables
   - [ ] Test error capturing
   - [ ] Configurare alert email per errori critici

   ## 🟢 NICE-TO-HAVE - Post MVP

   ### 6. Performance Optimization
   - [ ] Implementare Redis caching per query frequenti
   - [ ] Ottimizzare query N+1 con eager loading
   - [ ] Compressione asset statici con gzip
   - [ ] Setup CDN per asset (Cloudflare)
   ```

5. **Salva la pagina**

6. **Clicca "🤖 Genera Task"**
   - Dovrebbe aprirsi un modal
   - Vedi spinner "Analisi in corso..."
   - Dopo 3-5 secondi → Success!

7. **Verifica Modal**
   - ✅ Messaggio: "X task generati con successo"
   - ✅ Lista task con:
     - Emoji per tipo (💡 proposal, ⚙️ implementation, 🔬 validation)
     - Titolo task
     - Descrizione dettagliata
     - Badge difficoltà (colorato)
     - Badge fase (es. Development, Testing)
     - Badge tipo task
     - Equity reward (%)
   - ✅ Nota: "I task sono in stato 'suggested'..."
   - ✅ Pulsante "Vai al Progetto →"

8. **Vai al Progetto**
   - Clicca "Vai al Progetto →"
   - Dovresti vedere nuova sezione "Task Suggeriti" (se esiste nel template)
   - Oppure task con badge "SUGGESTED"

9. **Approva un Task**
   - Trova task suggerito
   - Clicca "Approva"
   - Task passa da `suggested` → `open`
   - Task diventa assegnabile

---

## Test 2: Permessi ✅

### Steps:
1. **Logout dal tuo account**
2. **Vai alla pagina wiki (senza login)**
   ```
   http://localhost:5000/wiki/<project_id>/page/mvp-production-checklist
   ```
3. **Verifica:** Pulsante "🤖 Genera Task" NON visibile (o se cliccato → redirect login)

4. **Login con altro account** (non creator/collaboratore)
5. **Vai alla stessa pagina wiki**
6. **Clicca "🤖 Genera Task"**
7. **Verifica:** Errore 403 "Non hai i permessi..."

---

## Test 3: Validazione Contenuto ✅

### Steps:
1. **Crea pagina wiki con contenuto breve**
   - Titolo: "Test Short"
   - Contenuto: "Troppo breve"  (< 100 caratteri)

2. **Clicca "🤖 Genera Task"**
3. **Verifica:** Errore "Il contenuto della pagina è troppo breve (minimo 100 caratteri)"

---

## Test 4: Task Duplicati ✅

### Steps:
1. **Vai alla pagina wiki "MVP Production Checklist"**
2. **Clicca "🤖 Genera Task"** (seconda volta)
3. **Verifica:** AI dovrebbe evitare task duplicati
   - Task già esistenti NON vengono ri-generati
   - Solo task nuovi/diversi vengono creati

---

## Test 5: Task Validation Type ✅

### Steps:
1. **Crea pagina wiki con esperimenti:**
   ```markdown
   ## Esperimenti di Validazione

   ### Test 1: Validare interesse utenti per feature X
   Vogliamo testare se gli utenti sono interessati alla feature di notifiche real-time.
   
   **Ipotesi:** Crediamo che almeno il 60% degli utenti attivi userebbe notifiche real-time.
   
   **Metodo:** Creare landing page con signup form e misurare conversion rate in 2 settimane.
   ```

2. **Genera task**
3. **Verifica:** Task di tipo `validation` ha campi:
   - `hypothesis`: "Crediamo che..."
   - `test_method`: Metodo concreto di test

---

## Expected Results (Cosa aspettarsi)

### ✅ Success Case:
```json
{
  "success": true,
  "message": "5 task generati con successo dalla pagina wiki",
  "tasks_created": 5,
  "wiki_page_title": "MVP Production Checklist",
  "tasks": [
    {
      "title": "Setup PostgreSQL database su Neon",
      "description": "Creare e configurare database PostgreSQL...",
      "task_type": "implementation",
      "phase": "Development",
      "difficulty": "Medium",
      "equity_reward": 4.5
    },
    ...
  ]
}
```

### ❌ Error Cases:
```json
// Contenuto breve
{
  "success": false,
  "error": "Il contenuto della pagina è troppo breve per generare task (minimo 100 caratteri)"
}

// Permessi
{
  "success": false,
  "error": "Non hai i permessi per generare task per questo progetto"
}

// AI Error
{
  "success": false,
  "error": "Non è stato possibile generare task dal contenuto della pagina. Riprova o modifica il contenuto."
}
```

---

## Troubleshooting

### Problema: "AI Service not available"
**Check:**
```bash
# Verifica OPENAI_API_KEY in .env
cat .env | grep OPENAI_API_KEY
```
**Soluzione:** Aggiungi/correggi `OPENAI_API_KEY` in `.env`

### Problema: Modal non si apre
**Check:** Console browser (F12) per errori JavaScript
**Soluzione:** 
- Verifica CSRF token valido
- Verifica URL endpoint corretto: `/api/ai-wiki/wiki/<id>/page/<slug>/generate-tasks`

### Problema: Task non appaiono in progetto
**Check:** Database
```python
from app import create_app, db
from app.models import Task

app = create_app()
with app.app_context():
    tasks = Task.query.filter_by(status='suggested').all()
    for t in tasks:
        print(f"{t.id}: {t.title} - {t.status}")
```

### Problema: "Connection Error" durante generazione
**Possibili cause:**
- Rate limit DeepSeek raggiunto
- Timeout rete
- API key non valida

**Soluzione:**
- Attendi 30-60 secondi
- Riprova
- Controlla logs: `logs/app.log`

---

## Logs da Controllare

### Success:
```
INFO: Generati 5 task da pagina wiki 'MVP Production Checklist' per progetto 123
```

### Errors:
```
ERROR: Errore API DeepSeek (tasks da wiki): Rate limit exceeded
ERROR: Errore generazione task da wiki: <exception details>
```

**Location:** `logs/app.log`

---

## Performance Benchmarks

### Timing atteso:
- **Request processing:** < 100ms
- **AI analysis:** 3-5 secondi
- **Database writes:** < 500ms (per 5-8 task)
- **Total:** ~3.5-6 secondi

### Resource usage:
- **Memory:** +10-20MB durante AI call
- **CPU:** Spike breve durante JSON parsing
- **Network:** ~5-10KB request/response

---

## ✅ Test Completato!

Se tutti i test passano:
- ✅ Feature è pronta per uso
- ✅ Può essere usata per dogfooding KickStorm
- ✅ Può essere documentata per utenti finali

---

## Next Steps

1. **Dogfooding:** Usa la feature per sviluppare KickStorm
2. **Feedback:** Raccogli feedback da team
3. **Iterate:** Migliora prompt AI se task generati non sono ottimali
4. **Monitor:** Controlla logs per errori in produzione
5. **Optimize:** Se troppo lento, considera caching

---

**Test Status:** ✅ Ready to Test
**Estimated Time:** 15-20 minuti
**Difficulty:** Easy

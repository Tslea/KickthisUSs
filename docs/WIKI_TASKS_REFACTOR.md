# 🔄 Refactoring: Genera Task da Wiki

**Data:** 22 Ottobre 2025  
**Tipo:** Refactoring per allineare funzionalità wiki con sistema standard task

---

## 📋 Problema Originale

La funzione "Genera Task" dalla wiki aveva un comportamento **diverso** dal sistema standard di generazione task del progetto:

### ❌ Implementazione Precedente
- **Modale custom** con stati loading/success/error
- **Funzione AI dedicata** `generate_tasks_from_wiki_analysis()` con logica separata
- **Display in-page** dei task generati nel modale
- Nessun redirect alla pagina progetto
- Workflow diverso dal resto dell'applicazione

### ✅ Sistema Standard (come funziona nel progetto)
- **Alert + Redirect** alla pagina progetto
- **Funzione AI unica** `generate_suggested_tasks()` riutilizzata
- Task creati con `status='suggested'` e `is_suggestion=True`
- Approvazione/rifiuto nella pagina progetto
- Workflow consistente

---

## 🛠️ Modifiche Effettuate

### 1. **Rimossa funzione AI duplicata** (`ai_services.py`)

**Prima:**
```python
def generate_tasks_from_wiki_analysis(wiki_content, project_pitch, ...):
    # ~150 righe di logica AI custom
    # System prompt diverso
    # Validazione separata
    ...
```

**Dopo:**
```python
# Funzione rimossa completamente ❌
# Ora si usa generate_suggested_tasks() per tutto ✅
```

---

### 2. **Refactoring endpoint API** (`api_ai_wiki.py`)

**Prima:**
```python
# Importava funzione custom
from app.ai_services import generate_tasks_from_wiki_analysis

# Usava logica custom
suggested_tasks = generate_tasks_from_wiki_analysis(...)

# Ritornava JSON con lista task per modale
return jsonify({
    'tasks': [...],
    'tasks_created': len(created_tasks),
    'wiki_page_title': wiki_page.title
})
```

**Dopo:**
```python
# Importa funzione standard
from app.ai_services import generate_suggested_tasks, AI_SERVICE_AVAILABLE

# Arricchisce description con contenuto wiki
enriched_description = f"""CONTESTO DAL PROGETTO:
{project.description}

ANALISI/CHECKLIST DALLA WIKI (pagina: {wiki_page.title}):
{wiki_page.content}

ISTRUZIONI: Analizza il documento wiki ed estrai task actionable..."""

# Usa funzione standard del progetto
suggested_tasks = generate_suggested_tasks(
    pitch=project.pitch or project.name,
    category=project.category,
    description=enriched_description,  # ✅ Contenuto wiki qui
    existing_tasks=existing_tasks
)

# Crea task nel DB con stessa logica di api_projects.py
# Ritorna JSON compatibile con alert + redirect
return jsonify({
    'success': True,
    'message': f'{len(created_tasks)} nuovi task generati...',
    'tasks': created_tasks
})
```

**Vantaggi:**
- ✅ Riuso codice esistente (DRY principle)
- ✅ Logica AI consistente in tutta l'app
- ✅ Manutenzione più semplice (un solo posto da modificare)
- ✅ Stessi prompt, stessa validazione, stesso comportamento

---

### 3. **Semplificato frontend** (`templates/wiki/view.html`)

**Prima (~120 righe):**
```javascript
// Funzione per aprire modale
function openGenerateTasksModal() { ... }

// Funzione per chiudere modale
function closeGenerateTasksModal() { ... }

// Funzione async con gestione stati complessa
async function generateTasksFromWiki() {
    // Gestione loading state
    // Gestione success state con rendering HTML
    // Popola lista task nel modale
    // Gestione error state
}

// HTML del modale (80+ righe)
<div id="generateTasksModal" class="hidden ...">
    <div id="loadingState">...</div>
    <div id="successState">
        <div id="tasksList"><!-- rendering dinamico --></div>
        <a href="progetto">Vai al Progetto</a>
    </div>
    <div id="errorState">...</div>
</div>
```

**Dopo (~30 righe):**
```javascript
// Event listener semplice (stile progetto standard)
const generateTasksBtn = document.getElementById('generateTasksFromWikiBtn');
if (generateTasksBtn) {
    generateTasksBtn.addEventListener('click', function() {
        const button = this;
        const originalHTML = button.innerHTML;
        button.disabled = true;
        button.innerHTML = `<svg class="animate-spin ...">...</svg> Elaborazione...`;

        fetch(`/api/wiki/${projectId}/page/${pageSlug}/generate-tasks`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken(),
                'Content-Type': 'application/json'
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success && data.tasks && data.tasks.length > 0) {
                alert(`${data.tasks.length} nuovi task generati dall'IA!`);
                window.location.href = `/projects/${projectId}`;  // ✅ Redirect
            } else {
                alert(data.message || 'Nessun task generato');
            }
        })
        .catch(err => alert('Errore di connessione'))
        .finally(() => {
            button.disabled = false;
            button.innerHTML = originalHTML;
        });
    });
}

// ❌ Nessun modale HTML necessario
```

**Vantaggi:**
- ✅ 90 righe di codice in meno
- ✅ Nessun modale da gestire
- ✅ UX consistente con resto app (alert + redirect)
- ✅ Più semplice da mantenere

---

## 🎯 Workflow Finale (Unificato)

### Per l'utente:

1. **Dalla pagina wiki:**
   - Clicca "🤖 Genera Task"
   - Vede spinner sul pulsante
   - Riceve alert con conferma
   - Viene **reindirizzato alla pagina progetto**

2. **Dalla pagina progetto:**
   - Vede i task con badge **"SUGGESTED"**
   - Può **approvare** (→ status: `open`, visibile a tutti)
   - Può **rifiutare** (→ eliminato)
   - Può decidere **privacy** (pubblico/privato)

### Per lo sviluppatore:

- **Una sola funzione AI** da manutenere: `generate_suggested_tasks()`
- **Un solo workflow** di approvazione task
- **Codice DRY** (Don't Repeat Yourself)
- **Manutenzione semplificata**

---

## 📊 Confronto Quantitativo

| Aspetto | Prima | Dopo | Diff |
|---------|-------|------|------|
| **Righe AI function** | ~150 | 0 (riuso) | -150 ⬇️ |
| **Righe endpoint API** | ~125 | ~95 | -30 ⬇️ |
| **Righe frontend JS** | ~120 | ~30 | -90 ⬇️ |
| **Righe HTML modale** | ~80 | 0 | -80 ⬇️ |
| **Funzioni AI totali** | 2 | 1 | -1 ⬇️ |
| **Workflow diversi** | 2 | 1 | -1 ⬇️ |
| **TOTALE LINEE** | ~475 | ~125 | **-350 righe (-73%)** 🎉 |

---

## ✅ Checklist Testing

- [x] Funzione `generate_tasks_from_wiki_analysis()` rimossa da `ai_services.py`
- [x] Endpoint `/api/wiki/<project_id>/page/<slug>/generate-tasks` refactorato
- [x] Frontend semplificato (rimosso modale, aggiunto alert+redirect)
- [x] Flask riavviato senza errori
- [ ] **Test manuale:** Cliccare "Genera Task" da pagina wiki
- [ ] **Verifica:** Task creati con `status='suggested'` nel DB
- [ ] **Verifica:** Redirect funziona verso pagina progetto
- [ ] **Verifica:** Task approvabili/rifiutabili dalla pagina progetto

---

## 🚀 Come Testare

1. **Apri una pagina wiki** del progetto (es. `/projects/4/wiki/cosa-manca-per-mvp`)
2. **Clicca "🤖 Genera Task"**
3. **Aspetta elaborazione** (spinner sul pulsante)
4. **Verifica alert** con numero task generati
5. **Vieni reindirizzato** alla pagina progetto automaticamente
6. **Nella pagina progetto:**
   - Trova i task nelle varie fasi (Planning, Development, etc.)
   - Verifica badge **"SUGGESTED"** sui task
   - Prova ad **approvare** un task (diventa pubblico)
   - Prova a **rifiutare** un task (viene eliminato)

---

## 📝 Note Tecniche

### Perché arricchire la `description`?

La funzione `generate_suggested_tasks()` accetta tre parametri:
- `pitch`: Breve descrizione del progetto
- `category`: Categoria progetto
- `description`: Descrizione dettagliata

Per passare il **contenuto wiki** all'AI, lo includiamo in `description` con contesto chiaro:

```python
enriched_description = f"""CONTESTO DAL PROGETTO:
{project.description}

ANALISI/CHECKLIST DALLA WIKI:
{wiki_page.content}

ISTRUZIONI: Analizza il documento wiki..."""
```

Questo permette all'AI di:
1. ✅ Capire il contesto del progetto
2. ✅ Leggere il contenuto wiki (checklist/roadmap/analisi)
3. ✅ Generare task specifici basati su entrambi

### Compatibilità con sistema esistente

Il refactoring **non rompe** nessuna funzionalità esistente:
- ✅ `generate_suggested_tasks()` funziona come prima
- ✅ Pulsante "Suggerisci Task AI" nella pagina progetto **inalterato**
- ✅ Approvazione/rifiuto task **inalterata**
- ✅ Database schema **inalterato**

---

## 🎉 Risultato

**Un sistema unificato e semplificato** per la generazione task AI, che:
- Riduce duplicazione codice (DRY)
- Migliora manutenibilità
- Garantisce UX consistente
- Semplifica testing
- Usa le stesse best practice in tutta l'app

**-350 righe di codice (-73%)** 🚀

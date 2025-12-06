# 🔄 Spiegazione Completa: Flusso GitHub vs Upload Diretto

## 📚 Indice
1. [Panoramica Sistema](#panoramica)
2. [Flusso GitHub (Pull Request)](#flusso-github)
3. [Flusso Upload Diretto](#flusso-upload)
4. [Confronto](#confronto)
5. [Quando Usare Quale](#quando-usare)
6. [Implementazione Tecnica](#implementazione)

---

## 🎯 Panoramica Sistema {#panoramica}

KICKStorm supporta **2 modalità principali** per sottomettere soluzioni:

```
┌─────────────────────────────────────────────────────┐
│            MODALITÀ DI CONTRIBUZIONE                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1️⃣  FLUSSO GITHUB (Pull Request)                  │
│      → Per progetti software con repository         │
│      → Contributi di codice trackabili              │
│      → Review automatizzata                         │
│                                                     │
│  2️⃣  FLUSSO UPLOAD DIRETTO                         │
│      → Per tutti gli altri tipi di contenuto        │
│      → Design, hardware, docs, media                │
│      → Validazione lato server                      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 💻 Flusso GitHub (Pull Request) {#flusso-github}

### 🎬 Come Funziona

```
┌─────────┐      ┌─────────┐      ┌──────────┐      ┌─────────────┐
│ Utente  │ ───→ │ GitHub  │ ───→ │  PR      │ ───→ │ KICKStorm   │
│  vede   │      │  Fork   │      │  aperta  │      │  valida     │
│  task   │      │ + code  │      │          │      │  e traccia  │
└─────────┘      └─────────┘      └──────────┘      └─────────────┘
```

### 📖 Step-by-Step per Utente

#### 1. **Trova un Task Software**
```
Task: "Aggiungi autenticazione Google"
Tipo: 💻 Software
Repository: https://github.com/owner/kickstorm-app
```

#### 2. **Fai Fork del Repository**
```bash
# Su GitHub.com:
1. Vai su https://github.com/owner/kickstorm-app
2. Click su "Fork" in alto a destra
3. Ora hai: https://github.com/TUO-USERNAME/kickstorm-app
```

#### 3. **Clona il Tuo Fork**
```bash
git clone https://github.com/TUO-USERNAME/kickstorm-app.git
cd kickstorm-app
git checkout -b feature/google-auth
```

#### 4. **Scrivi il Codice**
```python
# app/auth/google.py
from flask import redirect
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    # ... resto della config
)

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri)
```

#### 5. **Commit e Push**
```bash
git add .
git commit -m "feat: Add Google OAuth authentication"
git push origin feature/google-auth
```

#### 6. **Apri Pull Request su GitHub**
```
Su GitHub.com:
1. Vai al tuo fork: https://github.com/TUO-USERNAME/kickstorm-app
2. Click su "Pull Request"
3. Base: owner/kickstorm-app main
   Compare: TUO-USERNAME/kickstorm-app feature/google-auth
4. Titolo: "Add Google OAuth authentication"
5. Descrizione: Spiega cosa hai fatto
6. Click "Create Pull Request"

✅ PR creata: https://github.com/owner/kickstorm-app/pull/123
```

#### 7. **Invia Soluzione su KICKStorm**
```
Form KICKStorm:
┌────────────────────────────────────────────────┐
│ Tipo Contenuto: [💻 Software]                  │
│                                                │
│ 🔗 URL Pull Request:                           │
│ https://github.com/owner/kickstorm-app/pull/123│
│                                                │
│ 📝 Descrizione:                                │
│ Implementato OAuth con Google usando Authlib  │
│ - Login button nel template                   │
│ - Callback handler                            │
│ - User profile sync                           │
│                                                │
│          [Invia Soluzione] 🚀                  │
└────────────────────────────────────────────────┘
```

#### 8. **Sistema Verifica Automaticamente**
```python
# KICKStorm backend fa:
1. Parse URL della PR
2. Chiamata API GitHub:
   GET /repos/owner/kickstorm-app/pulls/123
3. Verifica:
   ✅ PR esiste
   ✅ Base branch è corretta
   ✅ Utente GitHub corrisponde
   ✅ Codice compila (se CI/CD attivo)
4. Salva nel database:
   - solution.pull_request_url = "..."
   - solution.github_status = "pending"
```

#### 9. **Review e Merge**
```
Maintainer del progetto:
1. Riceve notifica su GitHub
2. Fa code review
3. Richiede modifiche O approva
4. Merge nella branch principale

KICKStorm:
✅ Webhook riceve notifica "PR merged"
✅ Assegna punti automaticamente
✅ Chiude task se completato
```

### 🎁 Vantaggi Flusso GitHub

| Vantaggio | Descrizione |
|-----------|-------------|
| **🔍 Tracciabilità** | Ogni modifica è tracciata con commit hash |
| **👥 Collaborazione** | Code review integrata di GitHub |
| **🤖 CI/CD** | Test automatici prima del merge |
| **📊 Metriche** | Linee di codice, complessità, coverage |
| **🔙 Reversibilità** | Facile fare rollback se serve |
| **🏆 Portfolio** | PR nel tuo profilo GitHub pubblico |

### ⚠️ Svantaggi

- ❌ Richiede account GitHub
- ❌ Curva apprendimento Git
- ❌ Solo per codice/testo
- ❌ Non adatto a file binari grandi

---

## 📤 Flusso Upload Diretto {#flusso-upload}

### 🎬 Come Funziona

```
┌─────────┐      ┌─────────────┐      ┌──────────┐      ┌─────────┐
│ Utente  │ ───→ │  File       │ ───→ │ Server   │ ───→ │ Storage │
│  crea   │      │  Browser    │      │ Valida   │      │  S3 o   │
│  file   │      │  Upload     │      │          │      │  locale │
└─────────┘      └─────────────┘      └──────────┘      └─────────┘
```

### 📖 Step-by-Step per Utente

#### 1. **Trova un Task Non-Software**
```
Task: "Design logo per applicazione mobile"
Tipo: 🎨 Design Grafico
```

#### 2. **Crea i File**
```
Photoshop/Figma/Illustrator:
- logo_primary.ai       (sorgente vettoriale)
- logo_variations.psd   (varianti colore)
- logo_export.png       (1024x1024)
- logo_export.svg       (vettoriale web)
- guidelines.pdf        (manuale utilizzo)
```

#### 3. **Invia Soluzione su KICKStorm**
```
Form KICKStorm:
┌────────────────────────────────────────────────┐
│ Tipo Contenuto: [🎨 Design Grafico]            │
│                                                │
│ 📁 File Sorgente (AI/PSD/Figma):               │
│ [Scegli File] ✓ logo_primary.ai (2.4 MB)      │
│               ✓ logo_variations.psd (18 MB)   │
│                                                │
│ 📁 File Export (PNG/SVG/PDF):                  │
│ [Scegli File] ✓ logo_export.png (156 KB)      │
│               ✓ logo_export.svg (12 KB)       │
│               ✓ guidelines.pdf (890 KB)       │
│                                                │
│ 📝 Descrizione:                                │
│ Logo minimalista con 3 varianti colore        │
│ - Primary: Blu McLaren (#0066CC)              │
│ - Dark: Per sfondi scuri                      │
│ - Mono: Versione bianco/nero                  │
│                                                │
│          [Invia Soluzione] 🚀                  │
└────────────────────────────────────────────────┘
```

#### 4. **Sistema Valida e Salva**
```python
# KICKStorm backend fa:
1. Valida ogni file:
   - Estensione permessa per tipo design
   - Dimensione < 100MB (limite per design)
   - Nessun malware (antivirus scan)
   
2. Organizza in struttura GitHub:
   designs/
     ├── source/
     │   ├── logo_primary.ai
     │   └── logo_variations.psd
     └── export/
         ├── logo_export.png
         ├── logo_export.svg
         └── guidelines.pdf

3. Genera preview:
   - Thumbnail PNG
   - Metadata (risoluzione, colori)
   
4. Salva nel database:
   - solution.content_type = 'design'
   - solution_file records con content_category
```

#### 5. **Opzionale: Sync su GitHub**
```python
# Se progetto ha repo GitHub:
1. GitHubService crea branch: solution/123-design-logo
2. Commit file nella struttura corretta
3. Apre PR automatica
4. Link PR viene salvato in solution.pull_request_url

# Altrimenti:
- File rimangono solo su storage KICKStorm
- Nessun sync GitHub
```

### 🎁 Vantaggi Upload Diretto

| Vantaggio | Descrizione |
|-----------|-------------|
| **🚀 Semplicità** | Drag & drop, nessun Git necessario |
| **🎨 Tutti i Formati** | PSD, AI, FIG, MP4, CAD, qualsiasi file |
| **📦 File Grandi** | Fino a 500MB per video |
| **👤 Per Non-Dev** | Designer, maker, writer possono contribuire |
| **⚡ Veloce** | Upload diretto senza fork/clone |

### ⚠️ Svantaggi

- ❌ Nessun version control nativo
- ❌ Difficile fare modifiche iterative
- ❌ Nessuna review automatica
- ❌ Costi storage per file grandi

---

## ⚖️ Confronto Diretto {#confronto}

| Aspetto | Flusso GitHub 💻 | Upload Diretto 📤 |
|---------|------------------|-------------------|
| **Utente Target** | Sviluppatori | Designer, Maker, Writer |
| **Complessità** | Alta (Git, PR) | Bassa (Browser upload) |
| **Tipi File** | Codice, testo | Tutti (immagini, video, CAD) |
| **Size Limit** | ~10MB | Fino a 500MB |
| **Version Control** | ✅ Completo | ❌ Limitato |
| **Code Review** | ✅ Integrata | ❌ Manuale |
| **Preview** | ✅ Diff linea per linea | ✅ Thumbnail/preview |
| **Rollback** | ✅ Facile (git revert) | ❌ Difficile |
| **Tracciabilità** | ✅ Commit hash | ⚠️ Solo timestamp |
| **CI/CD** | ✅ Test automatici | ❌ Nessuna |
| **Portfolio** | ✅ GitHub public | ⚠️ Solo su KICKStorm |

---

## 🤔 Quando Usare Quale? {#quando-usare}

### ✅ Usa **FLUSSO GITHUB** quando:

```
✓ Task è tipo "Software" (codice)
✓ Progetto ha repository GitHub configurato
✓ Modifiche richiedono review tecnica
✓ Vuoi trackare modifiche nel tempo
✓ Team vuole CI/CD automatizzato
✓ Contributo è codice testabile

Esempi:
- "Implementa API REST per utenti"
- "Fixa bug nel sistema di pagamento"
- "Aggiungi unit test per auth module"
- "Refactoring database models"
```

### ✅ Usa **UPLOAD DIRETTO** quando:

```
✓ Task è tipo: Design, Hardware, Docs, Media
✓ File sono binari (PSD, AI, STL, MP4)
✓ Non serve version control complesso
✓ Utente non sa usare Git
✓ File sono molto grandi (>10MB)
✓ Modifiche sono "tutto o niente"

Esempi:
- "Design logo aziendale"
- "Crea modello 3D stampabile"
- "Scrivi documentazione utente PDF"
- "Registra video tutorial"
- "Disegna schemi CAD per PCB"
```

### 🔀 Situazioni **MISTE**:

```
Progetto complesso con più tipi:

Task 1: "Implementa dashboard" → GitHub (React code)
Task 2: "Design UI mockup" → Upload (Figma files)
Task 3: "Scrivi docs API" → Upload (PDF/DOCX)
Task 4: "Video demo app" → Upload (MP4)

💡 Ogni task può usare flusso diverso!
```

---

## 🛠️ Implementazione Tecnica {#implementazione}

### Database Schema

```sql
CREATE TABLE solution (
    id INTEGER PRIMARY KEY,
    task_id INTEGER NOT NULL,
    submitted_by_user_id INTEGER NOT NULL,
    solution_content TEXT,
    
    -- Campo tipo contenuto (NUOVO)
    content_type VARCHAR(20) DEFAULT 'software',
    -- Valori: software, hardware, design, documentation, media, mixed
    
    -- Per flusso GitHub
    pull_request_url VARCHAR(500),
    github_status VARCHAR(20),
    -- Valori: pending, merged, closed, rejected
    
    -- Per flusso upload
    file_path VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE solution_file (
    id INTEGER PRIMARY KEY,
    solution_id INTEGER NOT NULL,
    original_filename VARCHAR(255),
    stored_filename VARCHAR(255),
    file_path VARCHAR(500),
    
    -- Classificazione file (NUOVO)
    content_type VARCHAR(20),
    content_category VARCHAR(50),
    -- Esempi:
    --   content_type=design, content_category=logo
    --   content_type=hardware, content_category=pcb_schematic
    
    file_size INTEGER,
    mime_type VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Backend Routes

```python
# app/routes_tasks.py

@tasks_bp.route('/tasks/<int:task_id>/submit', methods=['POST'])
@login_required
def submit_solution_form(task_id):
    # 1. Ottieni content_type dal form
    content_type = request.form.get('content_type', 'software')
    
    # 2. Branch logic basata su tipo
    if content_type == 'software':
        # Flusso GitHub
        pull_request_url = request.form.get('pull_request_url')
        
        if pull_request_url:
            # Valida PR esiste
            pr_data = github_service.validate_pr_url(pull_request_url)
            if not pr_data:
                flash('Pull Request non valida', 'error')
                return redirect(...)
            
            # Crea soluzione
            solution = Solution(
                task_id=task_id,
                submitted_by_user_id=current_user.id,
                content_type='software',
                pull_request_url=pull_request_url,
                github_status='pending'
            )
        else:
            # Fallback: upload file codice
            files = request.files.getlist('files')
            # ... logica upload
    
    else:
        # Flusso upload diretto (design, hardware, docs, media)
        files = request.files.getlist('files')
        
        # Valida ogni file
        for file in files:
            validation = github_service.validate_file_upload(
                {'name': file.filename, 'size': len(file.read())},
                content_type
            )
            if not validation['valid']:
                flash(validation['error'], 'error')
                return redirect(...)
        
        # Salva file
        solution = Solution(
            task_id=task_id,
            submitted_by_user_id=current_user.id,
            content_type=content_type
        )
        db.session.add(solution)
        db.session.flush()
        
        for file in files:
            # Determina category specifico
            ext = file.filename.rsplit('.', 1)[1]
            category = determine_category(ext, content_type)
            
            solution_file = SolutionFile(
                solution_id=solution.id,
                original_filename=file.filename,
                content_type=content_type,
                content_category=category,
                # ... altri campi
            )
            db.session.add(solution_file)
    
    db.session.commit()
    return redirect(url_for('tasks.task_detail', task_id=task_id))
```

### Frontend Form

```html
<!-- submit_solution.html -->

<form method="POST" enctype="multipart/form-data">
    
    <!-- Selettore tipo contenuto -->
    {% include 'partials/_content_type_selector.html' %}
    
    <!-- Upload file dinamico -->
    {% include 'partials/_file_upload_multi.html' %}
    
    <!-- Sezione GitHub PR (solo per software) -->
    <div id="github-pr-section" style="display: none;">
        <label>URL Pull Request</label>
        <input type="url" name="pull_request_url" 
               placeholder="https://github.com/owner/repo/pull/123">
        <p>💡 Fai fork, crea codice, apri PR e incolla URL qui</p>
    </div>
    
    <!-- Descrizione -->
    <textarea name="solution_content"></textarea>
    
    <button type="submit">Invia Soluzione</button>
</form>

<script>
// Mostra sezione GitHub solo per tipo software
document.addEventListener('contentTypeChanged', function(e) {
    const type = e.detail.contentType;
    const githubSection = document.getElementById('github-pr-section');
    
    if (type === 'software' && projectHasGithub) {
        githubSection.style.display = 'block';
    } else {
        githubSection.style.display = 'none';
    }
});
</script>
```

---

## 📊 Statistiche Utilizzo

```
Distribuzione Flussi (esempio):

Software (GitHub):     45% ████████████████████
Design (Upload):       20% ████████
Hardware (Upload):     15% ██████
Docs (Upload):         12% ████
Media (Upload):         8% ███
```

---

## 🔮 Evoluzioni Future

### 1. **Hybrid Mode**
```
Utente può:
- Aprire PR su GitHub (codice)
- + Upload file di design nella stessa soluzione
- Sistema unisce entrambi i flussi
```

### 2. **GitHub LFS Integration**
```
Per file grandi in repository:
- Video demo in repo GitHub
- Usa Git LFS per storage efficiente
- KICKStorm tracka pointer file
```

### 3. **Auto-Detection**
```
Sistema analizza file caricati:
- Se sono .py, .js → Suggerisce flusso GitHub
- Se sono .psd, .ai → Conferma upload diretto
```

---

## 📖 Risorse Utente

### Guide Video
- 🎥 "Come fare una Pull Request su GitHub"
- 🎥 "Upload design su KICKStorm"
- 🎥 "Best practices per soluzioni hardware"

### Template
- 📄 `PR_TEMPLATE.md` - Template descrizione PR
- 📄 `SOLUTION_CHECKLIST.md` - Checklist pre-invio
- 📄 `FILE_ORGANIZATION.md` - Come organizzare file

---

## ❓ FAQ

**Q: Posso cambiare flusso dopo aver inviato?**
A: No, il tipo è immutabile. Crea una nuova soluzione.

**Q: Cosa succede se PR viene chiusa senza merge?**
A: Soluzione va in stato "rejected", no punti assegnati.

**Q: Posso caricare file anche per tipo software?**
A: Sì! GitHub PR + upload file documentazione extra.

**Q: Limite dimensioni totali?**
A: 500MB per soluzione, diviso tra tutti i file.

**Q: Come modifico file già caricati?**
A: Invia nuova soluzione con versione aggiornata.

---

## 🎯 Conclusione

**Flusso GitHub** = Professionale, tracciabile, per sviluppatori

**Upload Diretto** = Semplice, flessibile, per tutti

**Entrambi** = Essenziali per piattaforma completa! 🚀

# 🧪 Guida Test Git Sync Workspace

## Prerequisiti

1. ✅ **Git installato** (verificato: `git version 2.47.1.windows.2`)
2. ⚙️ **Configurazione GitHub**:
   - Variabile d'ambiente `GITHUB_ENABLED=true`
   - Variabile d'ambiente `GITHUB_TOKEN=ghp_...` (Personal Access Token)
   - Token deve avere permessi `repo` (full control)

## Test Manuale - Metodo 1: Via Interfaccia Web

### Step 1: Avvia l'applicazione
```bash
flask run
# oppure
python run.py
```

### Step 2: Crea/Seleziona un Progetto
1. Accedi all'applicazione
2. Vai a un progetto esistente O crea un nuovo progetto
3. **IMPORTANTE**: Il progetto deve avere un repository GitHub configurato:
   - Se non ce l'ha, vai su "Impostazioni Progetto" → "GitHub Repository"
   - Inserisci URL: `https://github.com/tua-org/tuo-repo` (o lascia vuoto per creazione automatica)

### Step 3: Vai alla Workspace
1. Nel progetto, vai alla tab "Workspace"
2. Dovresti vedere l'interfaccia di upload

### Step 4: Crea un ZIP di Test
Crea una cartella con alcuni file di test:
```
test_workspace/
├── src/
│   ├── main.py
│   └── utils.py
├── README.md
└── config.json
```

Crea lo ZIP:
```bash
# Windows PowerShell
Compress-Archive -Path test_workspace -DestinationPath test_workspace.zip

# Linux/Mac
zip -r test_workspace.zip test_workspace/
```

### Step 5: Upload ZIP
1. Clicca "Carica ZIP"
2. Seleziona `test_workspace.zip`
3. Attendi il caricamento

### Step 6: Verifica Risultato
Dovresti vedere uno di questi messaggi:

**✅ Se git sync funziona:**
```
✅ Sincronizzato su GitHub via Git (X file) • Vedi commit
```

**⏳ Se usa Celery (fallback):**
```
⏳ Sync avviato in background (Celery)...
```

### Step 7: Verifica su GitHub
1. Vai al repository GitHub del progetto
2. Dovresti vedere:
   - Nuovo commit con messaggio: "Upload workspace: X files via KickthisUSs"
   - Cartella `workspace/` con i tuoi file

---

## Test Manuale - Metodo 2: Via API (curl/Postman)

### Step 1: Login e Ottieni Session
```bash
# Login
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=tuo@email.com&password=tua_password" \
  -c cookies.txt

# Ottieni CSRF token (dalla pagina)
```

### Step 2: Upload ZIP
```bash
curl -X POST http://localhost:5000/api/projects/1/upload-zip \
  -H "X-CSRFToken: TUO_CSRF_TOKEN" \
  -b cookies.txt \
  -F "file=@test_workspace.zip"
```

### Step 3: Verifica Risposta
La risposta dovrebbe contenere:
```json
{
  "success": true,
  "session_id": "...",
  "file_count": X,
  "github_sync": {
    "success": true,
    "async": false,
    "method": "git",
    "message": "✅ Sync completato: X file caricati",
    "files_synced": X,
    "commit_url": "https://github.com/..."
  }
}
```

---

## Test Automatico - Script Python

Crea `test_git_sync.py`:

```python
import requests
import zipfile
import io
import os

# Configurazione
BASE_URL = "http://localhost:5000"
EMAIL = "tuo@email.com"
PASSWORD = "tua_password"
PROJECT_ID = 1  # ID del tuo progetto

# 1. Login
session = requests.Session()
login_resp = session.post(
    f"{BASE_URL}/auth/login",
    data={"email": EMAIL, "password": PASSWORD}
)
print(f"Login: {login_resp.status_code}")

# 2. Crea ZIP di test
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
    zip_file.writestr("src/main.py", "print('Hello from git sync!')")
    zip_file.writestr("README.md", "# Test Workspace")
zip_buffer.seek(0)

# 3. Upload ZIP
upload_resp = session.post(
    f"{BASE_URL}/api/projects/{PROJECT_ID}/upload-zip",
    files={"file": ("test.zip", zip_buffer, "application/zip")}
)

result = upload_resp.json()
print(f"\n📤 Upload Result:")
print(f"  Success: {result.get('success')}")
print(f"  Files: {result.get('file_count')}")

if result.get('github_sync'):
    sync = result['github_sync']
    print(f"\n🔄 GitHub Sync:")
    print(f"  Method: {sync.get('method')}")
    print(f"  Async: {sync.get('async')}")
    print(f"  Message: {sync.get('message')}")
    if sync.get('commit_url'):
        print(f"  Commit: {sync.get('commit_url')}")

# 4. Verifica su GitHub (manualmente)
print(f"\n✅ Test completato! Verifica su GitHub:")
print(f"   https://github.com/TUA_ORG/TUO_REPO")
```

Esegui:
```bash
python test_git_sync.py
```

---

## Debug e Troubleshooting

### Verifica Log
Controlla i log dell'applicazione per vedere quale metodo viene usato:

```python
# Nei log dovresti vedere:
# "Using git sync (synchronous) for project X"
# oppure
# "Git sync not available, using Celery async sync"
```

### Test Git Disponibilità
```python
from app.services.git_sync_service import GitSyncService
git_sync = GitSyncService()
print(f"Git sync enabled: {git_sync.is_enabled()}")
```

### Test Repository GitHub
```python
from app.models import Project
from app.services.github_sync_service import GitHubSyncService

project = Project.query.get(PROJECT_ID)
github_sync = GitHubSyncService()

# Verifica se repository esiste
if project.github_repo_name:
    print(f"Repository: {project.github_repo_name}")
else:
    # Crea repository
    repo_info = github_sync.setup_project_repository(project)
    print(f"Repository creato: {repo_info}")
```

### Errori Comuni

**❌ "Git command not available"**
- Soluzione: Git non è nel PATH o non installato
- Verifica: `git --version`

**❌ "GitHub token not configured"**
- Soluzione: Imposta `GITHUB_TOKEN` in `.env` o variabili d'ambiente

**❌ "Git clone failed: authentication failed"**
- Soluzione: Token GitHub non valido o scaduto
- Verifica: Crea nuovo token con permessi `repo`

**❌ "Git push failed: branch 'main' not found"**
- Soluzione: Il repository usa 'master' invece di 'main'
- Il codice prova automaticamente entrambi

---

## Checklist Test Completo

- [ ] Git installato e nel PATH
- [ ] `GITHUB_ENABLED=true` configurato
- [ ] `GITHUB_TOKEN` valido configurato
- [ ] Progetto ha repository GitHub (configurato o creato automaticamente)
- [ ] Upload ZIP funziona
- [ ] Messaggio mostra "via Git" (non Celery)
- [ ] File appaiono su GitHub in `workspace/`
- [ ] Commit creato con messaggio corretto
- [ ] Link al commit funziona nel frontend

---

## Performance

**Git Sync (sincrono):**
- ⚡ Veloce: ~2-5 secondi per 100 file
- ✅ Un solo commit per tutti i file
- ✅ Nessuna dipendenza da Celery

**GitHub API (fallback):**
- 🐌 Più lento: ~10-30 secondi per 100 file
- ⚠️ Rate limits GitHub
- ⚠️ Richiede Celery per non bloccare

---

## Successo! 🎉

Se vedi:
- ✅ Messaggio "Sincronizzato via Git"
- ✅ Commit su GitHub
- ✅ File in `workspace/` su GitHub

**Il sistema funziona correttamente!**


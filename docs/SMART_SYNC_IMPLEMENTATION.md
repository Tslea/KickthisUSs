# Smart Sync Implementation

## Overview
Smart Sync sostituisce la sincronizzazione file-per-file con GitHub usando un **singolo commit batch** per semplificare il flusso di lavoro per i fondatori non tecnici.

## Problema Risolto
**Prima**: Caricando un ZIP del progetto, ogni file veniva committato individualmente su GitHub, causando:
- 599 commit per il progetto Kickstorm caricato come ZIP
- Cronologia Git inquinata con commit di file di build, venv, node_modules
- Complessità eccessiva per utenti non tecnici

**Dopo**: Un singolo commit batch con tutti i file filtrati:
- 1 commit invece di 599
- Filtri automatici per file sensibili (`.env`, secrets, SSH keys)
- Filtri automatici per directory di build (`venv`, `node_modules`, `__pycache__`, `dist`, `build`)

## Architettura

### 1. Backend: `GitHubSyncService.sync_workspace_from_zip()`
**File**: `app/services/github_sync_service.py`

**Funzionalità**:
- Scansiona ricorsivamente la directory workspace
- Applica filtri di sicurezza via `is_file_safe()`:
  - Blocca: `.env`, `secrets.yml`, `credentials.json`, chiavi SSH, certificati
- Applica filtri di sincronizzazione via `should_sync_to_github()`:
  - Ignora: `venv/`, `node_modules/`, `__pycache__/`, `dist/`, `build/`, `.git/`
  - Ignora: `.pyc`, `.pyo`, `.log`, `.tmp`
- Usa GitHub Tree API per creare un unico commit batch
- Ritorna statistiche dettagliate:
  - `files_synced`: numero di file sincronizzati
  - `files_ignored`: file ignorati (build artifacts, cache)
  - `files_blocked`: file bloccati (secrets, keys)
  - `commit_sha`: SHA del commit creato
  - `commit_url`: URL GitHub del commit

**Esempio Response**:
```json
{
  "success": true,
  "commit_sha": "abc123...",
  "commit_url": "https://github.com/user/repo/commit/abc123",
  "files_synced": 42,
  "files_ignored": 150,
  "files_blocked": 2
}
```

### 2. API Endpoint: `POST /api/projects/<id>/upload-zip`
**File**: `app/api_uploads.py`

**Integrazione Smart Sync**:
1. Estrae il ZIP nella directory sessione
2. Salva metadata della sessione
3. **NUOVO**: Chiama `sync_workspace_from_zip()` se il progetto ha `github_repo_full_name`
4. Ritorna risposta con sezione `github_sync`:
```json
{
  "success": true,
  "session_id": "abc123",
  "file_count": 200,
  "total_size": 1234567,
  "github_sync": {
    "success": true,
    "commit_sha": "xyz789",
    "commit_url": "https://github.com/...",
    "files_synced": 42,
    "files_ignored": 150,
    "files_blocked": 2,
    "message": "✅ Workspace synced to GitHub in single commit: 42 files"
  }
}
```

### 3. Frontend: Notifica di Successo
**File**: `app/static/js/workspace.js`

**Visualizzazione**:
- Se `github_sync.success = true`: mostra "ZIP caricato (200 file) • ✅ Sincronizzato su GitHub (42 file in 1 commit)"
- Se `github_sync.success = false`: mostra "ZIP caricato (200 file) • ⚠️ Sync GitHub fallito: [error]"
- Se nessun `github_sync`: mostra solo "ZIP caricato (200 file)"

## Filtri di Sicurezza

### File Bloccati (`is_file_safe()`)
```python
BLOCKED_FILES = {
    '.env', '.env.local', '.env.production',
    'secrets.yml', 'secrets.json',
    'credentials.json', 'service-account.json',
    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519'
}

BLOCKED_EXTENSIONS = {
    '.key', '.pem', '.p12', '.pfx', '.jks',
    '.keystore', '.crt', '.der'
}
```

### Directory Ignorate (`should_sync_to_github()`)
```python
SYNC_BLACKLIST_DIRS = {
    'venv', 'virtualenv', '.venv',
    'node_modules', 'bower_components',
    '__pycache__', '.pytest_cache',
    'dist', 'build', 'target',
    '.git', '.svn', '.hg'
}

SYNC_BLACKLIST_PATTERNS = [
    '*.pyc', '*.pyo', '*.pyd',
    '*.log', '*.tmp', '*.temp',
    '.DS_Store', 'Thumbs.db'
]
```

## Test Coverage

### Test di Sicurezza
- 25/25 test passati per `is_file_safe()`
- Verifica blocco di `.env`, secrets, SSH keys, certificati
- Verifica passaggio di file legittimi (`app.py`, `README.md`, `config.py`)

### Test di Sincronizzazione
- 33/33 test passati per `should_sync_to_github()`
- Verifica ignore di `venv/`, `node_modules/`, `__pycache__/`
- Verifica passaggio di codice sorgente (`src/`, `app/`, `*.py`, `*.js`)

## Workflow Utente Finale

1. **Creazione Progetto**: L'utente crea un progetto via AI con GitHub integration enabled
2. **Sviluppo Locale**: L'utente sviluppa il progetto in locale (Visual Studio, PyCharm, etc.)
3. **Drag & Drop ZIP**: L'utente fa drag & drop del file ZIP nella dashboard Kickstorm
4. **Smart Sync Automatico**: 
   - Kickstorm estrae il ZIP
   - Filtra file sensibili e build artifacts
   - Crea **1 singolo commit** su GitHub
   - Mostra notifica: "✅ Sincronizzato su GitHub (42 file in 1 commit)"
5. **GitHub Pronto**: Il repository GitHub contiene solo il codice sorgente pulito

**Nessun comando Git richiesto** - tutto automatico!

## Miglioramenti Futuri

### Priorità Alta
- [ ] Diff-based sync: sincronizzare solo file modificati invece dell'intero workspace
- [ ] Progress indicator per workspace grandi (>1000 file)
- [ ] Link diretto al commit GitHub nella notifica

### Priorità Media
- [ ] Configurazione blacklist personalizzata per progetto
- [ ] Preview file sincronizzati prima del commit
- [ ] Rollback automatico se sync fallisce

### Priorità Bassa
- [ ] Supporto per `.gitignore` esistenti nel workspace
- [ ] Merge intelligente con branch esistenti
- [ ] Commit message personalizzato

## Note di Implementazione

### Sicurezza
- Tutti i file attraversano doppio filtro: `is_file_safe()` + `should_sync_to_github()`
- File bloccati NON vengono mai caricati su GitHub, nemmeno temporaneamente
- Logging completo di file ignorati/bloccati per audit

### Performance
- Tree API GitHub supporta fino a 100.000 file per commit
- Limite attuale: 200 file per ZIP upload (configurabile via `PROJECT_WORKSPACE_MAX_FILES`)
- Timeout: 30 secondi per upload + sync (configurabile)

### Compatibilità
- Funziona con progetti esistenti e nuovi
- Non richiede modifiche al database
- Backward compatible: progetti senza GitHub integration continuano a funzionare normalmente

## Troubleshooting

### Smart Sync Non Eseguito
**Sintomo**: ZIP caricato ma nessuna notifica GitHub
**Causa**: `project.github_repo_full_name` non configurato
**Soluzione**: Assicurarsi che il progetto abbia GitHub integration abilitato

### File Bloccati
**Sintomo**: Notifica "2 file bloccati"
**Causa**: File sensibili rilevati (`.env`, secrets, keys)
**Soluzione**: Rimuovere file sensibili dal ZIP prima dell'upload

### Sync Fallito
**Sintomo**: "⚠️ Sync GitHub fallito: authentication failed"
**Causa**: Token GitHub scaduto o invalido
**Soluzione**: Riconnettere account GitHub nelle impostazioni progetto

## References
- GitHub Tree API: https://docs.github.com/en/rest/git/trees
- PyGithub Documentation: https://pygithub.readthedocs.io/
- File Validation Best Practices: OWASP File Upload Cheat Sheet

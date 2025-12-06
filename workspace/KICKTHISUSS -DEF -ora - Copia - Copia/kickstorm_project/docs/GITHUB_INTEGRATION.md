# GitHub Integration Documentation

## Overview

KickThisUSS integra GitHub come backend invisibile per versioning e storage di progetti software/hardware. Gli utenti continuano a usare le stesse interfacce, ma dietro le quinte tutto viene versionato automaticamente.

## Caratteristiche

- **Automatico**: Repository creati automaticamente alla creazione progetto
- **Invisibile**: Utenti non vedono terminologia Git
- **Asincrono**: Operazioni GitHub non bloccano l'interfaccia
- **Resiliente**: Se GitHub fallisce, il sistema continua a funzionare
- **Retrocompatibile**: Progetti esistenti funzionano senza modifiche

## Setup

### 1. Configurazione Variabili Ambiente

Copia `.env.example` in `.env` e configura:

```bash
GITHUB_ENABLED=true
GITHUB_TOKEN=ghp_your_token_here
GITHUB_ORG=kickthisuss-projects
```

### 2. Crea GitHub Personal Access Token

1. Vai su GitHub → Settings → Developer settings → Personal access tokens
2. Genera nuovo token con permessi:
   - `repo` (full control)
   - `admin:org` (read/write)
3. Copia token in `.env`

### 3. Installa Dipendenze

```bash
pip install -r requirements.txt
```

### 4. Setup Database

```bash
flask db migrate -m "Add GitHub integration"
flask db upgrade
```

Oppure esegui lo script automatico:

```bash
python setup_github.py
```

### 5. Avvia Redis (per Celery)

```bash
# Windows (con Chocolatey)
choco install redis
redis-server

# Linux/Mac
sudo service redis-server start
```

### 6. Avvia Celery Worker

```bash
celery -A celery_worker.celery worker --loglevel=info
```

### 7. Avvia Flask

```bash
flask run
```

## Flusso Operativo

### Creazione Progetto

1. Utente crea progetto tramite form esistente
2. Progetto salvato nel database (comportamento normale)
3. **In background**: Task Celery crea repository GitHub
4. Repository URL salvato nel campo `project.github_repo_url`

### Proposta Soluzione

1. Utente invia soluzione tramite form esistente
2. Soluzione salvata nel database (comportamento normale)
3. **In background**: 
   - Crea branch `solution-{id}-{name}`
   - Carica file organizzati per tipo
   - Crea Pull Request
   - Salva info in `solution.github_pr_url`

### Visualizzazione File

- API `/api/github/project/{id}/files` lista contenuti
- API `/api/github/project/{id}/file/content` recupera file
- API `/api/github/solution/{id}/preview` genera anteprime

## Struttura Repository GitHub


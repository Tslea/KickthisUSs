# 📋 Piano di Azione per il Lancio

> Obiettivo: documentare i passaggi necessari per arrivare al go-live senza modificare ancora il codice esistente. Ogni sezione elenca attività incrementalmente eseguibili (“punto per punto”) mantenendo le funzionalità attuali intatte.

## 1. Accessibilità (A11y)
- [x] Audit completo degli elementi interattivi (`base.html`, `project_detail.html`, `auth/*.html`) per aggiungere `aria-label`, `role`, `aria-describedby`.
  - Nota: Navigazione, sezioni progetto e form auth ora hanno attributi ARIA e region label.
- [x] Aggiornare tutte le immagini pubbliche con `alt` descrittivi coerenti con il contenuto (wiki, progetti, dashboard).
  - Nota: Verificate tutte le occorrenze `<img>` e confermati alt contestuali.
- [x] Inserire skip link primario in `base.html` e verificare la navigazione da tastiera su viewport mobile/desktop.
  - Nota: Skip link presente e testato insieme a `aria-live` sui flash.
- [x] Uniformare gli stati di focus utilizzando classi Tailwind (`focus-visible:ring`, `outline-none` gestito) e verificare contrasto AA.
  - Nota: Introdotte utility `focus-ring`/`focus-ring-subtle` e applicate a pulsanti e link principali.

## 2. Sanitizzazione & Validazione Input
- [x] Introdurre helper `sanitize_html()` in `app/utils.py` usando `bleach` con whitelists definite.
  - Nota: Funzioni `clean_*_field` centralizzano whitelist e riutilizzano `bleach`.
- [x] Applicare sanitizzazione lato server per wiki, milestone, descrizioni progetto e commenti.
  - Nota: Route wiki/milestone/progetti/API commenti ora puliscono input prima del salvataggio.
- [x] Sincronizzare validazioni client/server: pattern regex, lunghezze e messaggi coerenti tra moduli Flask-WTF e JS.
  - Nota: Creato `validation_rules.py`, helper Python e `validation.js` con dataset condiviso.
- [x] Rafforzare `file_validation.py` con controllo MIME reale (python-magic) e limiti dimensionali configurabili.
  - Nota: Validazione file ora supporta estensioni configurabili, dimensioni personalizzate e logga MIME/estensione.

## 3. Gestione Transazioni Database
- [x] Creare context manager `db_transaction()` riutilizzabile in `app/utils.py`.
  - Nota: Aggiunto context manager con commit/rollback centralizzati e importato dove necessario.
- [x] Aggiornare operazioni multi-step critiche (`routes_projects.py`, `routes_tasks.py`, `api_solutions.py`, servizi equity) per usare il context manager.
  - Nota: Create/update progetto, task CRUD, API soluzioni e `EquityService` ora usano il nuovo helper (inclusi sync GitHub).
- [x] Documentare linee guida per l’uso nelle PR future (mini sezione in README/CONTRIBUTING).
  - Nota: Inserita sezione “Database Transaction Guidelines” in `README.md`.

## 4. Performance & Asset Pipeline
- [ ] Profilare route principali per individuare query N+1 e applicare `joinedload/selectinload`.
- [ ] Configurare caching leggero (Flask-Caching) per pagine pubbliche e API di lettura.
- [ ] Abilitare lazy loading (`loading="lazy"`) su cover, avatar, thumbnail ed eventuali carousels.
- [ ] Aggiornare script NPM per build/minify Tailwind e JS (`npm run build:prod`) e integrare nella pipeline di deploy.

## 5. SEO & Discoverability
- [ ] Consolidare blocchi Jinja dei meta tag in `base.html` (description, keywords, og, twitter).
- [ ] Definire template JSON-LD per homepage e pagine progetto, includendo URL canonical.
- [ ] Creare checklist SEO per nuove pagine (title unico, headings ordinati, link interni).

## 6. Error Handling & Feedback
- [ ] Mappare errori comuni in `app/utils.py` (es. `ERROR_MESSAGES`) e uniformare flash/JSON response.
- [ ] Introdurre overlay/caricamenti riutilizzabili per azioni asincrone (upload cover, toggle milestone, invio inviti).
- [ ] Garantire che ogni chiamata fetch gestisca retry base e messaggi user-friendly.
- [ ] **Barra di Caricamento Globale**: Implementare progress bar visibile durante operazioni lunghe
  - [ ] Creare componente `LoadingBar` riutilizzabile in `base.html`
  - [ ] Mostrare progresso % per upload file grandi (workspace ZIP)
  - [ ] Integrare con fetch API per tracking upload/download
  - [ ] Aggiungere animazione skeleton per caricamenti contenuto

## 6b. Workspace Versioning & History
> ⚡ **PRINCIPIO GUIDA: Deve essere la cosa più intuitiva che esiste al mondo.**
> Zero curve di apprendimento. Un bambino di 8 anni deve capirlo al primo sguardo.
> Niente terminologia tecnica (no "commit", no "hash"). Solo: "Salva versione" → "Vedi cronologia" → "Torna indietro".

- [ ] **Storico Versioni Workspace**: Implementare sistema di versioning per file workspace
  - [ ] Creare modello `WorkspaceVersion` con campi: `id`, `project_id`, `user_id`, `timestamp`, `comment`, `file_hash`
  - [ ] Salvare snapshot ad ogni upload con timestamp automatico
  - [ ] Permettere all'utente di aggiungere commento descrittivo (come commit message)
- [ ] **UI Storico Versioni**: Sezione dedicata nella pagina workspace - **SEMPLICISSIMA**
  - [ ] Timeline verticale visiva con icone e colori 
  - [ ] Ogni versione mostra: 📅 "2 ore fa", 👤 avatar autore, 💬 commento
  - [ ] UN SOLO BOTTONE grande e chiaro: "⏪ Torna a questa versione"
  - [ ] Preview thumbnail/anteprima della versione (se possibile)
  - [ ] Niente tabelle complesse, niente colonne tecniche
- [ ] **Form Upload con Commento** - **DRAG & DROP + UN CAMPO**:
  - [ ] Zona drag-and-drop ENORME con animazione invitante
  - [ ] Campo unico: "Cosa hai cambiato?" (placeholder: "Ho aggiunto il logo" / "Corretto errori")
  - [ ] Barra progresso GRANDE e colorata durante upload
  - [ ] Conferma con animazione celebrativa ✨ "Salvato!"
- [ ] **Interazioni One-Click**:
  - [ ] Scaricare versione = 1 click
  - [ ] Ripristinare = 1 click + conferma ("Sei sicuro? Tornerai alla versione del 3 dicembre")
  - [ ] Confrontare = slider before/after (tipo app foto)
- [ ] **API Versioning**:
  - [ ] `GET /api/project/{id}/workspace/versions` - Lista versioni
  - [ ] `GET /api/project/{id}/workspace/versions/{version_id}` - Scarica versione specifica
  - [ ] `POST /api/project/{id}/workspace/versions/{version_id}/restore` - Ripristina versione

## 7. Testing Strategy
- [ ] Stabilire obiettivo coverage (>=70%) e configurare `pytest --cov`.
- [ ] Aggiungere test unitari per modelli critici (User, Project, Milestone, WikiPage).
- [ ] Scrivere test integrazione per flussi chiave (creazione progetto, aggiunta milestone, upload cover).
- [ ] Pianificare smoke test E2E (Playwright/Selenium) per onboarding e collaborazione progetto.

## 8. Documentazione & Developer Experience
- [ ] Integrare docstring e type hints nei servizi core e nelle route più complesse.
- [ ] Aggiornare README/DEPLOYMENT_CHECKLIST con i nuovi step (build asset, migrazioni, test).
- [ ] Creare guida rapida “Come contribuire” che includa standard di code style, naming classi Tailwind e gestione notifiche.

## 9. Infra, Monitoring & GTM (post-tech)
- [ ] Selezionare stack hosting (es. Heroku/Render) con DB gestito, Redis e storage upload (S3) già documentati.
- [ ] Integrare monitoring (Sentry + APM) e analytics privacy-friendly.
- [ ] Pianificare onboarding guidato in-app, help center e policy (Privacy, ToS, FAQ) per il go-live.

## 10. Internazionalizzazione (i18n) & Supporto Multilingua
- [ ] **Setup Flask-Babel**: Installare `flask-babel` e configurare in `app/__init__.py`
  - [ ] Aggiungere `babel.cfg` per estrazione messaggi
  - [ ] Configurare lingue supportate (IT, EN come minimo)
  - [ ] Settare lingua di default e fallback
- [ ] **Estrazione Stringhe**: Creare workflow per estrarre/aggiornare traduzioni
  - [ ] Marcare tutte le stringhe UI con `_()` o `gettext()` in template Python
  - [ ] Usare `{% trans %}` in template Jinja2
  - [ ] Eseguire `pybabel extract` per generare `.pot`
- [ ] **File Traduzioni**: Creare e mantenere file `.po` per ogni lingua
  - [ ] `/translations/it/LC_MESSAGES/messages.po` (Italiano)
  - [ ] `/translations/en/LC_MESSAGES/messages.po` (Inglese)
  - [ ] Opzionali: ES (Spagnolo), FR (Francese), DE (Tedesco)
- [ ] **Compilazione**: Configurare build step `pybabel compile` per generare `.mo`
- [ ] **Selector Lingua**: Implementare dropdown/selector lingua in navbar
  - [ ] Salvare preferenza in session/cookie
  - [ ] Integrare con `@babel.localeselector`
- [ ] **Contenuti Dinamici**: Gestire traduzioni per contenuti utente
  - [ ] Nomi progetto, descrizioni (multilingua opzionale)
  - [ ] Email template in più lingue
  - [ ] Notifiche sistema tradotte
- [ ] **Testing i18n**: Verificare tutte le pagine in ogni lingua supportata
  - [ ] Homepage, About, How it Works
  - [ ] Dashboard, Progetti, Task
  - [ ] Form di auth (login, register, reset password)
  - [ ] Messaggi flash e errori
- [ ] **SEO Multilingua**: Configurare `hreflang` e URL localizzati
  - [ ] `/it/projects`, `/en/projects`, etc.
  - [ ] Sitemap multilingua
  - [ ] Meta tag `og:locale`

---

## 11. 🚀 CHECKLIST FINALE PRE-LANCIO MVP

### 🔐 Sicurezza Critica (BLOCCA LANCIO SE NON RISOLTO)
- [ ] **SECRET_KEY:** Rimuovere fallback hardcoded da `app/config.py` L8
  - [ ] Generare chiave sicura: `python -c "import secrets; print(secrets.token_hex(32))"`
  - [ ] Settare variabile d'ambiente `SECRET_KEY` nel server di produzione
  - [x] ✅ Verificare che `.env` NON sia committato su GitHub (già in .gitignore)

### 🔒 Configurazione Ambiente Produzione
- [ ] **Flask Environment:** Settare `FLASK_ENV=production` (attualmente `FLASK_DEBUG=1`)
- [ ] **Database:** Configurare `DATABASE_URL` su Neon PostgreSQL (template già in .env)
- [x] ✅ **Email SMTP:** Gmail già configurato (`kickthisuss@gmail.com`)
- [x] ✅ **API Keys:** GROK configurato (`grok-4-fast`)
- [x] ✅ **GitHub:** Token e Org configurati (Tslea)

### 🛡️ Sicurezza & Privacy
- [ ] **HTTPS:** Verificare che HTTPS sia attivo su Google Cloud Run (auto con custom domain)
- [x] ✅ **Cookie Banner:** Implementato in `base.html` con accept/decline GDPR
- [ ] **Dockerfile Security:** Aggiungere `USER nonroot` (gira come root)
- [ ] **Rate Limiting:** Configurare Redis per produzione (attualmente `memory://`)
- [ ] **Backup Database:** Configurare backup automatici su Neon

### ✅ Test & Validazione
- [ ] **Test Suite:** Eseguire `python -m pytest --cov=app --cov-fail-under=80`
- [ ] **Test Manuale Completo:**
  - [ ] Registrazione nuovo utente
  - [ ] Verifica email (controllare inbox)
  - [ ] Login con credenziali
  - [ ] Setup 2FA (opzionale ma testare)
  - [ ] Creazione progetto
  - [ ] Upload file/cover
  - [ ] Creazione task
  - [ ] Invio soluzione
  - [ ] Reset password
- [ ] **Cross-Browser:** Testare su Chrome, Firefox, Safari, Edge
- [ ] **Mobile Responsive:** Verificare layout su dispositivi mobile

### 📧 Email & Comunicazioni
- [x] ✅ **Template Email:** Esistono verify, welcome, reset
- [ ] **SPF/DKIM/DMARC:** Configurare record DNS per deliverability (Gmail)
- [x] ✅ **Sender Email:** `kickthisuss@gmail.com` configurato

### 📄 Legal & Compliance
- [x] ✅ **Privacy Policy:** Aggiornata (6 dicembre 2025, hosting Google Cloud Run)
- [x] ✅ **Terms of Service:** Accessibili
- [x] ✅ **Cookie Policy:** Implementato banner GDPR
- [x] ✅ **GDPR Compliance:** Delete account implementato

### 🎨 UX & Contenuti
- [ ] **Error Pages:** Verificare che 404, 500, 429 siano personalizzate
- [ ] **Notifiche:** Testare sistema notifiche (badge, lista)
- [ ] **Flash Messages:** Verificare user-friendly
- [ ] **Loading States:** Verificare feedback azioni async

### 📊 Monitoring & Analytics
- [x] ✅ **Sentry:** Configurato in `app/__init__.py` (DSN da settare in .env)
- [ ] **Uptime Monitor:** Configurare Better Uptime
- [x] ✅ **Google Analytics:** Configurato in `base.html` (Measurement ID da settare)
- [x] ✅ **Logging:** Rotation configurata in `app/__init__.py`

### 🚀 Deployment
- [ ] **Build Assets:** Verificare `npm run build:prod`
- [ ] **Database Migrations:** Preparare `flask db upgrade`
- [ ] **Static Files:** Verificare CSS/JS serviti
- [ ] **Environment Variables:** Settare tutte le var su Google Cloud Run
- [ ] **Rollback Plan:** Documentare procedura

### 📋 Post-Lancio Immediato (Prime 24-48h)
- [ ] **Smoke Test Produzione:** Testare tutti i flussi critici su URL produzione
- [ ] **Monitoring Attivo:** Monitorare errori Sentry e log server
- [ ] **Email di Test:** Inviare email di test per verificare deliverability
- [ ] **Feedback Loop:** Preparare canale per raccogliere feedback utenti beta

### 🟡 Issue Medie (Risolvere entro 1 settimana)
- [ ] Dockerfile: Aggiungere USER non-root per sicurezza
- [ ] Password: Considerare aumentare minimo da 6 a 8+ caratteri
- [ ] Antivirus: Valutare integrazione ClamAV per scan file upload (post-MVP)

### 🟢 Issue Basse (Roadmap Post-Lancio)
- [ ] Encryption: Considerare criptare `totp_secret` e `backup_codes` a riposo
- [ ] Soft Delete: Implementare soft-delete per compliance GDPR
- [ ] Email Service: Valutare migrazione a SendGrid/Mailgun

---

## 12. 🔧 SERVIZI ESTERNI DA CONFIGURARE

### Servizi OBBLIGATORI (Go-Live)
| Servizio | Scopo | URL | Variabile .env | Status |
|----------|-------|-----|----------------|--------|
| **Neon** | Database PostgreSQL | [neon.tech](https://neon.tech) | `DATABASE_URL` | ⏳ Da configurare |
| **Google Cloud Run** | Hosting | [console.cloud.google.com](https://console.cloud.google.com) | Deploy | ⏳ Da configurare |
| **Sentry** | Error Tracking | [sentry.io](https://sentry.io) | `SENTRY_DSN` | ⏳ Da configurare |
| **Google Analytics 4** | Analytics | [analytics.google.com](https://analytics.google.com) | `GA_MEASUREMENT_ID` | ⏳ Da configurare |

### Servizi OPZIONALI (Raccomandati)
| Servizio | Scopo | URL | Note |
|----------|-------|-----|------|
| **Better Uptime** | Uptime Monitoring | [betteruptime.com](https://betteruptime.com) | Ping ogni 3 min, alert email |
| **Cloudflare** | CDN + SSL | [cloudflare.com](https://cloudflare.com) | Free tier, protegge da DDoS |
| **Google Domains** | Custom Domain | - | Per `kickthisuss.com` |

### 📝 Procedura Setup Servizi

#### 1. Neon PostgreSQL (5 min)
```bash
# 1. Crea account su neon.tech
# 2. Crea nuovo progetto "kickthisuss"
# 3. Seleziona regione Europa (Germany/Frankfurt)
# 4. Copia connection string
# 5. Aggiungi a .env:
DATABASE_URL=postgresql://user:password@ep-xxx.eu-central-1.aws.neon.tech/kickthisuss?sslmode=require
```

#### 2. Sentry (5 min)
```bash
# 1. Crea account su sentry.io
# 2. Crea nuovo progetto Flask/Python
# 3. Copia DSN
# 4. Aggiungi a .env:
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

#### 3. Google Analytics 4 (5 min)
```bash
# 1. Vai su analytics.google.com
# 2. Crea nuova proprietà "KickthisUSs"
# 3. Crea data stream Web
# 4. Copia Measurement ID
# 5. Aggiungi a .env:
GA_MEASUREMENT_ID=G-XXXXXXXXXX
```

#### 4. Google Cloud Run (10 min)
```bash
# 1. Vai su console.cloud.google.com
# 2. Abilita Cloud Run API
# 3. Collega repository GitHub
# 4. Configura build da Dockerfile
# 5. Setta environment variables:
#    - SECRET_KEY (generato)
#    - DATABASE_URL (Neon)
#    - SENTRY_DSN
#    - GA_MEASUREMENT_ID
#    - MAIL_* (tutte le email vars)
#    - GROK_API_KEY
#    - GITHUB_TOKEN, GITHUB_ORG
#    - FLASK_ENV=production
# 6. Deploy!
```

---

### 🎯 Go/No-Go Decision

**LANCIO BLOCCATO SE:**
- ❌ SECRET_KEY fallback presente in codice (da risolvere)
- ❌ HTTPS non attivo (auto su Cloud Run)
- ❌ Test suite fallisce
- ~~❌ Cookie banner GDPR mancante~~ ✅ FATTO

**LANCIO OK SE:**
- ✅ SECRET_KEY settato come env var su Cloud Run
- ✅ Database Neon configurato
- ✅ Sentry attivo
- ✅ Test manuali passati
- ✅ Email funzionanti

---

## 📊 RIEPILOGO STATO ATTUALE

### ✅ GIÀ COMPLETATO
| Area | Item | Note |
|------|------|------|
| Accessibilità | ARIA, skip links, focus | Sezione 1 completa |
| Sanitizzazione | bleach, validation | Sezione 2 completa |
| Database | Transaction manager | Sezione 3 completa |
| Privacy Policy | Aggiornata 6/12/2025 | Google Cloud Run EU |
| Terms of Service | Aggiornati | Email corretta |
| Cookie Banner | GDPR compliant | Accept/Decline |
| Delete Account | Implementato | GDPR compliant |
| Email | Gmail SMTP | kickthisuss@gmail.com |
| AI Provider | GROK grok-4-fast | Funzionante |
| GitHub Sync | Token + Org | Tslea |
| Sentry (codice) | SDK integrato | DSN da settare |
| GA4 (codice) | Script in base.html | ID da settare |
| Logging | Rotation configurata | logs/app.log |
| Terminologia | TEMPLE system | Centralizzato |

### ⏳ DA FARE PRIMA DEL LANCIO
| Priorità | Item | Tempo | Note |
|----------|------|-------|------|
| 🔴 CRITICO | SECRET_KEY produzione | 2 min | Generare e settare |
| 🔴 CRITICO | Neon Database | 5 min | Creare DB e connection string |
| 🔴 CRITICO | FLASK_ENV=production | 1 min | Settare env var |
| 🟡 ALTO | Sentry DSN | 5 min | Creare progetto sentry.io |
| 🟡 ALTO | GA4 Measurement ID | 5 min | Creare proprietà |
| 🟡 ALTO | Cloud Run deploy | 10 min | Configurare e deploy |
| 🟡 ALTO | Test manuali | 30 min | Tutti i flussi |
| 🟢 MEDIO | Better Uptime | 5 min | Monitoring URL |
| 🟢 MEDIO | DNS SPF/DKIM | 10 min | Per deliverability email |

### ⏭️ POST-LANCIO
- Dockerfile USER nonroot
- Password minimo 8 caratteri
- Internazionalizzazione (EN)
- Performance profiling

---

📌 **Nota operativa:** eseguire ogni sezione in ordine di priorità (Accessibilità ➝ Sanitizzazione ➝ Performance … ➝ **Checklist Finale**). Aggiornare questo file barrando i checkbox completati prima di toccare il codice, così da mantenere traccia dello stato senza rischiare regressioni.


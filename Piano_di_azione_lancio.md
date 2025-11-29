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

---

📌 **Nota operativa:** eseguire ogni sezione in ordine di priorità (Accessibilità ➝ Sanitizzazione ➝ Performance …). Aggiornare questo file barrando i checkbox completati prima di toccare il codice, così da mantenere traccia dello stato senza rischiare regressioni.


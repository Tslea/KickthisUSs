# 🚀 KickthisUSs - Piattaforma di Collaborazione e Investimenti

**KickthisUSs** è una piattaforma innovativa che combina gestione progetti collaborativa con un sistema di investimenti basato su votazione comunitaria. Gli utenti possono creare progetti, collaborare con altri membri e partecipare a un ecosistema di investimenti democratico.

## ✨ Caratteristiche Principali

### 🏗️ Gestione Progetti
- **Creazione Progetti**: Interface intuitiva per creare e pubblicare progetti
- **Task Management**: Sistema completo di gestione task con stati e assegnazioni
- **Collaborazione**: Inviti e gestione collaboratori con ruoli definiti
- **Soluzioni AI**: Integrazione con AI per suggerimenti e soluzioni automatiche

### 💰 Sistema di Investimenti
- **Votazione Mensile**: La community vota i migliori progetti pubblici ogni mese
- **Selezione Automatica**: I progetti più votati accedono alla piattaforma investimenti
- **Equity Investment**: Possibilità di acquistare equity nei progetti o contribuire gratuitamente
- **Configurazione Flessibile**: I team configurano la distribuzione equity (default 1% KickthisUSs)

### 👥 Community Features
- **Profili Utente**: Profili personalizzabili con statistiche e progetti
- **Inviti Progetti**: Sistema di invito per collaborazioni
- **Notifiche**: Sistema di notifiche per aggiornamenti importanti
- **Wiki Collaborativa**: Knowledge base condivisa per progetti e competenze

### 🎨 Modern UI/UX
- **Design Responsive**: Interface ottimizzata per desktop e mobile
- **Tailwind CSS**: Styling moderno con componenti custom
- **Animazioni**: Transizioni fluide e feedback visivo
- **Dark/Light Mode**: Supporto per temi chiari e scuri

## 🏗️ Architettura Tecnica

### Backend
- **Flask**: Framework web Python con architettura modular
- **SQLAlchemy**: ORM per gestione database con migrazioni
- **Flask-Login**: Sistema di autenticazione e gestione sessioni
- **Blueprint Architecture**: Codice organizzato in moduli specializzati

### Frontend
- **Jinja2**: Template engine con componenti riutilizzabili
- **Tailwind CSS**: Framework CSS utility-first per styling
- **JavaScript ES6+**: Interattività lato client e chiamate AJAX
- **Material Icons**: Iconografia coerente e professionale

### Database
- **SQLite**: Database relazionale per sviluppo
- **Migrazioni**: Sistema di versioning schema database
- **Relazioni Complex**: Modelli interconnessi per progetti, utenti, investimenti

## 📦 Installazione

### Prerequisiti
```bash
- Python 3.8+
- pip (Python package installer)
- Git per version control
```

### Setup Ambiente
```bash
# Clone repository
git clone https://github.com/kickthisuss/kickstorm-project.git
cd kickstorm-project

# Crea virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure
venv\Scripts\activate     # Windows

# Installa dependencies
pip install -r requirements.txt

# Setup database
flask db upgrade

# Avvia applicazione
python run.py
```

### Configurazione
```bash
# Crea file .env per configurazioni locali
DATABASE_URL=sqlite:///instance/dev.db
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
```

## 🚀 Utilizzo

### 1. Registrazione e Login
- Crea un account sulla piattaforma
- Completa il profilo con informazioni e skills
- Explora progetti pubblici esistenti

### 2. Creazione Progetti
- Usa il form "Crea Progetto" per iniziare
- Aggiungi descrizione dettagliata e obiettivi
- Invita collaboratori tramite username
- Pubblica il progetto per ricevere voti

### 3. Gestione Task
- Aggiungi task specifici al tuo progetto
- Assegna task ai collaboratori
- Tracka progress con stati (todo/in_progress/completed)
- Ricevi suggerimenti AI per soluzioni

### 4. Sistema Investimenti
- **Votazione**: Vota progetti interessanti ogni mese
- **Investimenti**: Investi nei progetti selezionati dalla community
- **Equity**: Acquista percentuali di equity o contribuisci gratuitamente
- **Configurazione**: Se sei collaboratore, configura distribuzione equity

### 5. Community Engagement
- Partecipa alle discussioni nei progetti
- Contribuisci alla Wiki con conoscenze
- Ricevi notifiche per aggiornamenti importanti
- Costruisci la tua reputazione nella community

## 📊 Funzionalità del Sistema di Investimenti

### Flusso Mensile
1. **Votazione**: Utenti votano progetti pubblici (1 voto per progetto al mese)
2. **Selezione**: Progetti più votati diventano "InvestmentProject"
3. **Configurazione**: Team imposta prezzo equity e percentuali
4. **Investimenti**: Community investe con denaro o contributi gratuiti
5. **Tracking**: Monitoraggio equity venduta, investitori, capitali raccolti

### Distribuzione Equity
- **1% KickthisUSs**: Fisso per sostenere la piattaforma
- **10-30% Investitori**: Configurabile dal team progetto
- **69-89% Team**: Resto distribuito tra collaboratori

## 🔒 Sicurezza e Permessi

### Controlli Accesso
- **Progetti Privati**: Solo collaboratori invitati possono accedere
- **Investimenti**: Solo utenti non-collaboratori possono investire
- **Configurazioni**: Solo collaboratori possono modificare settings
- **Votazione**: Solo utenti registrati possono votare

### Validazioni
- Constraint database per integrità dati
- Validazioni lato server per tutti i form
- Sanitizzazione input utente
- Rate limiting su azioni critiche

## 🛠️ Struttura Progetto

```
kickstorm_project/
├── app/                          # Application package
│   ├── templates/               # Jinja2 templates
│   │   ├── investments/        # Investment system templates
│   │   ├── projects/          # Project management templates
│   │   └── users/            # User profile templates
│   ├── static/               # Static assets (CSS, JS, images)
│   ├── models.py            # Database models
│   ├── routes_*.py         # Route blueprints
│   └── api_*.py           # API endpoints
├── migrations/            # Database migrations
├── instance/             # Instance-specific files
├── requirements.txt     # Python dependencies
└── run.py              # Application entry point
```

## 📈 Roadmap Future

### Features Pianificate
- [ ] **Pagamenti Reali**: Integrazione Stripe/PayPal per transazioni
- [ ] **Mobile App**: App React Native per iOS/Android
- [ ] **Analytics Dashboard**: Metriche avanzate per projects e investimenti
- [ ] **API Public**: REST API per integrazioni esterne
- [ ] **Blockchain Integration**: Smart contracts per equity e governance

### Miglioramenti Tecnici
- [ ] **Caching**: Redis per performance migliori
- [ ] **Queue Jobs**: Celery per task background
- [ ] **Testing**: Coverage completa con pytest
- [ ] **Docker**: Containerization per deployment
- [ ] **CI/CD**: Pipeline automatizzate GitHub Actions

## 🤝 Contributing

Benvenuti contributi dalla community! Per contribuire:

1. Forka il repository
2. Crea branch feature (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Apri Pull Request con descrizione dettagliata

### Code Style
- Segui PEP 8 per Python
- Usa nomi descriptivi per variabili e funzioni  
- Commenta codice complex
- Scrivi test per nuove features

## 📝 License

Questo progetto è licenziato sotto MIT License - vedi file [LICENSE](LICENSE) per dettagli.

## 📞 Support

Per supporto e domande:
- **Email**: support@kickthisuss.com
- **GitHub Issues**: Per bug reports e feature requests
- **Discord**: Community Discord server per discussioni

---

### 🎉 Status Progetto: **PRODUCTION READY**

Il sistema è completamente implementato con:
- ✅ Sistema investimenti funzionante
- ✅ Interface utente moderna e responsive  
- ✅ Database con relazioni complete
- ✅ Security e validation layer
- ✅ Documentation completa

**Avvia l'applicazione con `python run.py` e visita http://127.0.0.1:5000** 🚀
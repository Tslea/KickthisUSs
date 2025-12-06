# 🧪 TEST WORKFLOW COMPLETO - MVP KICKTHISUSS

## 📋 CHECKLIST TEST END-TO-END

### **FASE 1: Setup Environment (5 min)**
- [ ] Verificare che il server sia in esecuzione (`python run.py`)
- [ ] Verificare che il database SQLite esista (`instance/dev.db`)
- [ ] Aprire browser su `http://localhost:5000`
- [ ] Verificare che non ci siano errori in console

### **FASE 2: Registrazione & Autenticazione (10 min)**
- [ ] **Registra User1 (Creator):**
  - Username: `test_creator`
  - Email: `creator@test.com`
  - Password: `Test1234!`
- [ ] **Verifica Email:**
  - ⚠️ Se email service non configurato, vai direttamente al database:
    ```sql
    UPDATE user SET email_verified = 1 WHERE username = 'test_creator';
    ```
- [ ] **Login User1:**
  - Verifica che il login funzioni
  - Verifica che la sessione sia persistente

- [ ] **Registra User2 (Contributor):**
  - Username: `test_contributor`
  - Email: `contributor@test.com`
  - Password: `Test1234!`
- [ ] **Verifica Email User2** (stessa procedura)
- [ ] **Login User2**

### **FASE 3: Creazione Progetto (5 min)**
- [ ] **Login come User1 (Creator)**
- [ ] **Crea Nuovo Progetto:**
  - Titolo: `Test MVP Equity System`
  - Categoria: `Software Development`
  - Pitch: `Sistema per testare distribuzione automatica equity`
  - Description: `Progetto di test per validare workflow completo equity`
  - Project Type: `Commercial`
  - Creator Equity: `5.0%`
- [ ] **Verifica Creazione:**
  - Progetto appare nella lista
  - Redirect alla pagina project_detail funziona
  - ✅ **AI Guide generata** (se OPENAI_API_KEY configurato)

### **FASE 4: Verifica Equity Initialization (CRITICO - 5 min)**
- [ ] **Vai al Cap Table:**
  - Click sul pulsante "Cap Table Dettagliata" nel progetto
  - URL dovrebbe essere `/project/<id>/equity`
- [ ] **Verifica Creator Equity:**
  - [ ] Creator (`test_creator`) ha **100.00%** equity iniziale
  - [ ] Total Distributed: **0.00%**
  - [ ] Available Equity: **94.00%** (100 - 5 creator - 1 platform)
  - [ ] Progress bar al 100%
- [ ] **Verifica Database (opzionale):**
  ```sql
  SELECT * FROM project_equity WHERE project_id = <project_id>;
  -- Dovrebbe esserci 1 record con equity_percentage = 100.0
  ```

### **FASE 5: Creazione Task con Equity Reward (5 min)**
- [ ] **Ancora come User1 (Creator)**
- [ ] **Crea Task:**
  - Titolo: `Implementare sistema di login`
  - Descrizione: `Creare sistema autenticazione con Flask-Login`
  - Task Type: `Backend Development`
  - Phase: `Implementazione`
  - Difficulty: `Medio`
  - **Equity Reward: `5.0%`** ⬅️ **IMPORTANTE**
  - Private: No
- [ ] **Verifica Task Creato:**
  - Task appare nella lista del progetto
  - **Equity reward visibile** nella card (`5.00% Equity`)
  - Click sul task per aprire dettaglio

### **FASE 6: Verifica UI Equity Reward (2 min)**
- [ ] **Nel Task Detail:**
  - [ ] Badge arancione con "5.00% Equity" visibile nell'header
  - [ ] Descrizione task completa
  - [ ] Sezione "Submit Solution" presente

### **FASE 7: Submit Solution (5 min)**
- [ ] **Logout User1**
- [ ] **Login come User2 (Contributor)**
- [ ] **Vai al Task creato:**
  - Navigate: Projects → `Test MVP Equity System` → Task `Implementare sistema di login`
- [ ] **Submit Solution:**
  - Solution Content: 
    ```
    Ho implementato il sistema di login con Flask-Login:
    - Configurazione LoginManager
    - Route /login e /logout
    - User loader callback
    - Protezione routes con @login_required
    
    Codice testato e funzionante!
    ```
  - Opzionale: Upload file (se vuoi testare)
- [ ] **Verifica Solution Submitted:**
  - Messaggio successo
  - Solution appare nella lista solutions del task
  - Status: "Pending"

### **FASE 8: Approve Solution & Equity Distribution (CRITICO - 10 min)**
- [ ] **Logout User2**
- [ ] **Login come User1 (Creator)**
- [ ] **Vai al Task**
- [ ] **Approve Solution:**
  - Click sul pulsante "Approve" nella solution di User2
  - Conferma approval
- [ ] **Verifica Immediate:**
  - [ ] Task status cambia a "Approved"
  - [ ] Solution status cambia a "Approved"
  - [ ] Messaggio successo con equity info

- [ ] **Verifica Notifica Equity (User2):**
  - [ ] Logout User1
  - [ ] Login User2
  - [ ] Check notifiche (bell icon)
  - [ ] **Dovrebbe esserci notifica:** 
    > "🎉 Hai guadagnato 5.0% equity sul progetto 'Test MVP Equity System' completando il task 'Implementare sistema di login'!"

### **FASE 9: Verifica Cap Table Updated (CRITICO - 5 min)**
- [ ] **Come User1 o User2:**
- [ ] **Vai al Cap Table:**
  - URL: `/project/<id>/equity`
- [ ] **Verifica Distribuzione:**
  - [ ] **Creator (`test_creator`)**: **95.00%** (era 100%, ora -5% distribuita)
  - [ ] **Contributor (`test_contributor`)**: **5.00%** (NEW!)
  - [ ] **Total Distributed**: **5.00%**
  - [ ] **Available Equity**: **89.00%** (94 - 5 distribuita)
- [ ] **Verifica Progress Bars:**
  - [ ] Progress bar Creator al 95%
  - [ ] Progress bar Contributor al 5%
  - [ ] Ranking corretto (Creator #1, Contributor #2)

### **FASE 10: Verifica Equity History (CRITICO - 5 min)**
- [ ] **Vai a Equity History:**
  - Click sul pulsante "Equity History & Audit" nel progetto
  - URL: `/project/<id>/equity/history`
- [ ] **Verifica Timeline Events:**
  - [ ] **Event 1 (più recente)**: 
    - Action: ✓ GRANTED
    - User: `test_contributor`
    - Equity Change: **+5.00%**
    - Before: 0.00% → After: 5.00%
    - Reason: "Task completion reward"
    - Source: `task_completion`
    - Changed By: 🤖 Automatic
  - [ ] **Event 2 (iniziale)**:
    - Action: 🚀 INITIAL
    - User: `test_creator`
    - Equity Change: **+100.00%**
    - Before: 0.00% → After: 100.00%
    - Reason: "Initial creator equity"
    - Source: `initial`
- [ ] **Verifica Stats:**
  - [ ] Total Equity Grants: **2**
  - [ ] Total Equity Distributed: **105.00%** (100 initial + 5 granted)

### **FASE 11: Verifica Dashboard Equity Personale (5 min)**
- [ ] **User2 Dashboard:**
  - [ ] Login User2
  - [ ] Vai a Profile: `/profile/test_contributor`
  - [ ] **Sezione Equity Portfolio:**
    - Total Equity Points: **5.00%**
    - Progetti Attivi: **1**
    - Media Equity: **5.00%**
  - [ ] **Breakdown per progetto:**
    - Progetto: `Test MVP Equity System`
    - Equity: **5.00%**
    - Progress bar al 5%

- [ ] **User1 Dashboard:**
  - [ ] Login User1
  - [ ] Vai a Profile: `/profile/test_creator`
  - [ ] **Sezione Equity Portfolio:**
    - Total Equity Points: **95.00%**
    - Progetti Attivi: **1**
    - Media Equity: **95.00%**

### **FASE 12: Test Scenario Complesso (Opzionale - 15 min)**
- [ ] **Crea secondo task (User1):**
  - Titolo: `Design interfaccia utente`
  - Equity Reward: **3.0%**
- [ ] **Submit solution (User2)**
- [ ] **Approve solution (User1)**
- [ ] **Verifica Cap Table:**
  - Creator: **95.00%** (unchanged, già distribuita)
  - Contributor: **8.00%** (5 + 3)
  - Available: **86.00%** (89 - 3)
- [ ] **Verifica Equity History:**
  - 3 eventi totali (initial + grant1 + grant2)
  - Ordine cronologico inverso

### **FASE 13: Test Edge Cases (Opzionale - 10 min)**
- [ ] **Test Equity Limit:**
  - [ ] Crea task con equity_reward > Available Equity
  - [ ] Prova ad approve → Dovrebbe fallire con errore
- [ ] **Test Multiple Contributors:**
  - [ ] Registra User3
  - [ ] Submit solution su nuovo task
  - [ ] Approve → Verifica cap table con 3 utenti

---

## 🎯 CRITERI DI SUCCESSO MVP

### ✅ **CORE FUNCTIONALITY (MUST WORK)**
- [x] Registrazione utenti funziona
- [x] Login/Logout funziona
- [x] Creazione progetto funziona
- [x] **Equity initialization automatica** (100% al creator)
- [x] Creazione task con equity reward funziona
- [x] Submit solution funziona
- [x] **Approve solution → Equity distribution automatica**
- [x] Cap table mostra distribuzione corretta
- [x] Equity history registra tutti i cambiamenti
- [x] Dashboard equity personale aggiornato
- [x] **Notifica equity granted** inviata al contributor

### ⚠️ **KNOWN ISSUES (Can be fixed post-MVP)**
- [ ] Email verification richiede MAIL_* env variables
- [ ] AI Guide generation richiede OPENAI_API_KEY
- [ ] Session cookie changes on server restart (SECRET_KEY non persistente)

---

## 🐛 DEBUGGING TIPS

### **Problema: Equity non inizializzata**
```sql
-- Check database
SELECT * FROM project_equity WHERE project_id = <id>;
-- Se vuoto, equity_service.initialize_creator_equity() non è stato chiamato
```

### **Problema: Equity non distribuita dopo approval**
```python
# Check logs
# Cerca: "✅ Granted X% equity to user Y"
# Se manca, distribute_task_completion_equity() ha fallito
```

### **Problema: Cap table vuota**
```python
# Check se ProjectEquity records esistono
SELECT user_id, equity_percentage FROM project_equity WHERE project_id = <id>;
```

### **Problema: Notifica non ricevuta**
```sql
-- Check notifications table
SELECT * FROM notification WHERE user_id = <contributor_id> AND type = 'equity_granted';
```

---

## 📝 TEST RESULTS LOG

**Date:** _____________

**Tester:** _____________

### Risultati:
- [ ] TUTTI i test core passati (FASE 1-11)
- [ ] Test complessi passati (FASE 12)
- [ ] Test edge cases passati (FASE 13)

### Bugs Trovati:
1. ______________________________
2. ______________________________
3. ______________________________

### Note:
______________________________
______________________________
______________________________

---

## 🚀 NEXT STEPS POST-TEST

Se tutti i test passano:
1. ✅ Setup .env completo (SECRET_KEY, OPENAI_API_KEY, MAIL_*)
2. ✅ Test con email verification reale
3. ✅ Deploy su staging server
4. ✅ Test con utenti reali

Se ci sono failures:
1. ❌ Identifica il punto di failure
2. ❌ Check logs (`logs/app.log`)
3. ❌ Fix il bug
4. ❌ Re-run test workflow

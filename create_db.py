# create_db.py
from app import create_app, db

print("--- Avvio creazione database ---")
app = create_app()
with app.app_context():
    print(">>> Contesto dell'applicazione creato.")
    try:
        db.create_all()
        print(">>> SUCCESS! Database e tabelle create correttamente.")
    except Exception as e:
        print(f"!!! ERRORE durante la creazione del database: {e}")
print("--- Fine processo ---")

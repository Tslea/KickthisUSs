# check_db.py
from app import create_app
from app.extensions import db
from app.models import SolutionFile

app = create_app()
with app.app_context():
    # Forza la creazione delle tabelle se non esistono
    db.create_all()
    print("✅ Tutte le tabelle sono state create/verificate")
    print(f"Tabelle nel database: {list(db.metadata.tables.keys())}")

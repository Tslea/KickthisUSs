"""
Migration per aggiungere supporto cartelle al sistema Wiki.
Aggiunge i campi: is_folder, parent_id, display_order
"""

import sys
import os

# Aggiungi il percorso del progetto al PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from flask import current_app
from app import create_app, db
from sqlalchemy import inspect, text

def upgrade():
    """Aggiunge i nuovi campi per le cartelle"""
    app = create_app()
    with app.app_context():
        # Aggiungi colonne se non esistono già
        try:
            # Verifica se le colonne esistono già
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('wiki_page')]
            
            print(f"Colonne esistenti: {columns}")
            
            if 'is_folder' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE wiki_page ADD COLUMN is_folder BOOLEAN DEFAULT 0 NOT NULL"))
                    conn.commit()
                print("[OK] Aggiunta colonna is_folder")
            
            if 'parent_id' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE wiki_page ADD COLUMN parent_id INTEGER"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wiki_page_parent_id ON wiki_page(parent_id)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_wiki_page_is_folder ON wiki_page(is_folder)"))
                    conn.commit()
                print("[OK] Aggiunta colonna parent_id e indici")
            
            if 'display_order' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE wiki_page ADD COLUMN display_order INTEGER DEFAULT 0 NOT NULL"))
                    conn.commit()
                print("[OK] Aggiunta colonna display_order")
            
            # Per SQLite, le colonne TEXT sono già nullable di default
            # Non serve modificare content
            
            print("[SUCCESS] Migration completata con successo!")
            
        except Exception as e:
            print(f"[ERROR] Errore durante la migration: {e}")
            import traceback
            traceback.print_exc()
            raise

def downgrade():
    """Rimuove i campi aggiunti"""
    app = create_app()
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('wiki_page')]
            
            if 'display_order' in columns:
                with db.engine.connect() as conn:
                    # SQLite non supporta DROP COLUMN direttamente, serve ricreare la tabella
                    print("[WARNING] SQLite non supporta DROP COLUMN. Per rimuovere le colonne, ricrea la tabella.")
            
            print("[SUCCESS] Rollback completato!")
            
        except Exception as e:
            print(f"[ERROR] Errore durante il rollback: {e}")
            raise

if __name__ == '__main__':
    print("Avvio migration per aggiungere supporto cartelle Wiki...")
    upgrade()
    print("Migration completata!")


"""
Migration per aggiungere supporto milestone/roadmap ai progetti.
Crea la tabella milestone con tutti i campi necessari.
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
    """Crea la tabella milestone"""
    app = create_app()
    with app.app_context():
        try:
            # Verifica se la tabella esiste già
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'milestone' not in tables:
                # Crea la tabella milestone
                with db.engine.connect() as conn:
                    conn.execute(text("""
                        CREATE TABLE milestone (
                            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                            project_id INTEGER NOT NULL,
                            title VARCHAR(200) NOT NULL,
                            description TEXT,
                            target_date DATE,
                            completed BOOLEAN NOT NULL DEFAULT 0,
                            completed_at DATETIME,
                            completed_by INTEGER,
                            display_order INTEGER NOT NULL DEFAULT 0,
                            created_by INTEGER NOT NULL,
                            created_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL,
                            FOREIGN KEY(project_id) REFERENCES project (id),
                            FOREIGN KEY(created_by) REFERENCES user (id),
                            FOREIGN KEY(completed_by) REFERENCES user (id)
                        )
                    """))
                    
                    # Crea gli indici
                    conn.execute(text("CREATE INDEX idx_milestone_project_id ON milestone(project_id)"))
                    conn.execute(text("CREATE INDEX idx_milestone_completed ON milestone(completed)"))
                    conn.execute(text("CREATE INDEX idx_milestone_created_by ON milestone(created_by)"))
                    
                    conn.commit()
                print("[OK] Tabella milestone creata con successo")
            else:
                print("[INFO] Tabella milestone già esistente")
            
            print("[SUCCESS] Migration completata con successo!")
            
        except Exception as e:
            print(f"[ERROR] Errore durante la migration: {e}")
            import traceback
            traceback.print_exc()
            raise

def downgrade():
    """Rimuove la tabella milestone"""
    app = create_app()
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'milestone' in tables:
                with db.engine.connect() as conn:
                    conn.execute(text("DROP TABLE IF EXISTS milestone"))
                    conn.commit()
                print("[OK] Tabella milestone rimossa")
            
            print("[SUCCESS] Rollback completato!")
            
        except Exception as e:
            print(f"[ERROR] Errore durante il rollback: {e}")
            raise

if __name__ == '__main__':
    print("Avvio migration per aggiungere supporto milestone...")
    upgrade()
    print("Migration completata!")


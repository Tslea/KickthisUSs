"""
Migration per aggiungere la tabella project_repository al database.
"""

import sys
import os
from sqlalchemy import inspect, text

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import create_app, db


def upgrade():
    """Crea la tabella project_repository."""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table("project_repository"):
            db.engine.execute(text("""
                CREATE TABLE project_repository (
                    id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL UNIQUE,
                    provider VARCHAR(50) NOT NULL DEFAULT 'local',
                    repo_name VARCHAR(255),
                    branch VARCHAR(100) NOT NULL DEFAULT 'main',
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    last_sync_at DATETIME,
                    created_at DATETIME,
                    updated_at DATETIME,
                    PRIMARY KEY (id),
                    FOREIGN KEY(project_id) REFERENCES project (id) ON DELETE CASCADE
                )
            """))
            db.engine.execute(text("CREATE INDEX ix_project_repository_provider ON project_repository (provider)"))
            db.engine.execute(text("CREATE INDEX ix_project_repository_status ON project_repository (status)"))
            print("[OK] Tabella project_repository creata con successo")
        else:
            print("[INFO] Tabella project_repository già esistente, nessuna azione richiesta.")


def downgrade():
    """Rimuove la tabella project_repository."""
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        if inspector.has_table("project_repository"):
            db.engine.execute(text("DROP TABLE project_repository"))
            print("[OK] Tabella project_repository rimossa con successo")
        else:
            print("[INFO] La tabella project_repository non esiste, niente da fare.")


if __name__ == '__main__':
    print("Avvio migration per aggiungere supporto project_repository...")
    upgrade()
    print("Migration completata!")


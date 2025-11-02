"""
Migration: Add Free Proposals System
Created: 2025-10-26
Description: Aggiunge supporto per proposte libere che aggregano più task o propongono nuovi task
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from sqlalchemy import text

def upgrade():
    """Crea le tabelle per le proposte libere"""
    
    app = create_app()
    with app.app_context():
        # Crea tabella free_proposals
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS free_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                developer_id INTEGER NOT NULL,
                
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                
                -- Equity richiesta
                equity_requested FLOAT NOT NULL,
                
                -- Tipo di proposta: 'multi_task' o 'new_task'
                proposal_type VARCHAR(50) NOT NULL,
                
                -- Dettagli se è un nuovo task proposto
                new_task_details TEXT,
                
                -- Status: 'pending', 'accepted', 'rejected'
                status VARCHAR(20) DEFAULT 'pending',
                
                -- Motivazione della decisione
                decision_note TEXT,
                decided_at DATETIME,
                
                -- GitHub Integration (come le soluzioni normali)
                github_branch_name VARCHAR(200),
                github_pr_url VARCHAR(500),
                github_pr_number INTEGER,
                github_commit_sha VARCHAR(40),
                github_synced_at DATETIME,
                
                -- Privacy
                is_public BOOLEAN DEFAULT 1,
                
                -- Timestamps
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
                FOREIGN KEY (developer_id) REFERENCES user (id) ON DELETE CASCADE
            )
        """))
        
        # Crea indici per performance
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_free_proposals_project 
            ON free_proposals(project_id)
        """))
        
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_free_proposals_developer 
            ON free_proposals(developer_id)
        """))
        
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_free_proposals_status 
            ON free_proposals(status)
        """))
        
        # Crea tabella di associazione proposal_tasks (many-to-many)
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS proposal_tasks (
                proposal_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                
                PRIMARY KEY (proposal_id, task_id),
                FOREIGN KEY (proposal_id) REFERENCES free_proposals (id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES task (id) ON DELETE CASCADE
            )
        """))
        
        db.session.commit()
        print("✅ Tabelle free_proposals e proposal_tasks create con successo")

def downgrade():
    """Rimuove le tabelle per le proposte libere"""
    app = create_app()
    with app.app_context():
        db.session.execute(text("DROP TABLE IF EXISTS proposal_tasks"))
        db.session.execute(text("DROP TABLE IF EXISTS free_proposals"))
        db.session.commit()
        print("✅ Tabelle free_proposals e proposal_tasks rimosse")

if __name__ == '__main__':
    print("🚀 Esecuzione migration: add_free_proposals")
    upgrade()
    print("✅ Migration completata!")

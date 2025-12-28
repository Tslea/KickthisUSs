#!/usr/bin/env python3
"""
Script per cancellare tutte le sessioni di upload senza toccare i progetti o i repository.

ATTENZIONE: Questo script rimuove SOLO le sessioni di upload temporanee.
NON tocca:
- I repository gestiti (directory 'repo/')
- I progetti nel database
- Altri file di configurazione

Cosa rimuove:
- Tutte le directory in {workspace_root}/{project_id}/incoming/{session_id}/
- I file history.json (opzionale, ma sicuro)
"""

import os
import sys
import shutil
import json
from pathlib import Path

# Aggiungi il percorso del progetto al Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.workspace_utils import get_workspace_root, ensure_project_workspace, history_file, load_history_entries


def cleanup_all_sessions(dry_run=False, clear_history=False):
    """
    Rimuove tutte le sessioni di upload per tutti i progetti.
    
    Args:
        dry_run: Se True, mostra solo cosa verrebbe rimosso senza effettuare modifiche
        clear_history: Se True, cancella anche i file history.json
    """
    app = create_app()
    
    with app.app_context():
        workspace_root = get_workspace_root()
        
        if not os.path.exists(workspace_root):
            print(f"[OK] Workspace root non esiste: {workspace_root}")
            print("  Nessuna sessione da rimuovere.")
            return
        
        print(f"[INFO] Workspace root: {workspace_root}")
        print()
        
        total_sessions = 0
        total_size = 0
        projects_processed = 0
        
        # Itera su tutte le directory dei progetti
        for project_dir in os.listdir(workspace_root):
            project_path = os.path.join(workspace_root, project_dir)
            
            # Salta se non è una directory
            if not os.path.isdir(project_path):
                continue
            
            # Verifica che sia un ID numerico (opzionale ma sicuro)
            try:
                project_id = int(project_dir)
            except ValueError:
                print(f"[WARN] Salto directory non numerica: {project_dir}")
                continue
            
            projects_processed += 1
            incoming_dir = os.path.join(project_path, 'incoming')
            repo_dir = os.path.join(project_path, 'repo')
            
            # Verifica che esista la directory incoming
            if not os.path.exists(incoming_dir):
                print(f"  Progetto {project_id}: nessuna directory 'incoming'")
                continue
            
            # Lista tutte le sessioni nella directory incoming
            sessions = []
            for session_id in os.listdir(incoming_dir):
                session_path = os.path.join(incoming_dir, session_id)
                
                # Salta se non è una directory
                if not os.path.isdir(session_path):
                    continue
                
                # Calcola la dimensione della sessione
                session_size = 0
                try:
                    for root, dirs, files in os.walk(session_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                session_size += os.path.getsize(file_path)
                            except (OSError, FileNotFoundError):
                                pass
                except (OSError, PermissionError):
                    pass
                
                sessions.append({
                    'session_id': session_id,
                    'path': session_path,
                    'size': session_size
                })
            
            if sessions:
                print(f"  Progetto {project_id}: {len(sessions)} sessione/i")
                for sess in sessions:
                    size_mb = sess['size'] / (1024 * 1024)
                    total_sessions += 1
                    total_size += sess['size']
                    
                    if dry_run:
                        print(f"    [DRY RUN] Rimuoverei: {sess['session_id']} ({size_mb:.2f} MB)")
                    else:
                        try:
                            shutil.rmtree(sess['path'], ignore_errors=True)
                            print(f"    [OK] Rimossa: {sess['session_id']} ({size_mb:.2f} MB)")
                        except Exception as e:
                            print(f"    [ERR] Errore rimuovendo {sess['session_id']}: {e}")
                
                # Pulisci anche history.json se richiesto
                if clear_history:
                    history_path = history_file(project_id)
                    if os.path.exists(history_path):
                        if dry_run:
                            print(f"    [DRY RUN] Cancellerei: {history_path}")
                        else:
                            try:
                                os.remove(history_path)
                                print(f"    [OK] Rimossa history: {history_path}")
                            except Exception as e:
                                print(f"    [ERR] Errore rimuovendo history: {e}")
            else:
                print(f"  Progetto {project_id}: nessuna sessione")
            
            # Verifica che la directory repo sia ancora intatta
            if os.path.exists(repo_dir):
                print(f"    [OK] Repository gestito intatto: {repo_dir}")
        
        print()
        print("=" * 60)
        if dry_run:
            print(f"[DRY RUN] Totale: {total_sessions} sessioni, {total_size / (1024 * 1024):.2f} MB")
            print("  Nessuna modifica effettuata. Esegui senza --dry-run per rimuovere.")
        else:
            print(f"[OK] Completato: {total_sessions} sessioni rimosse, {total_size / (1024 * 1024):.2f} MB liberati")
            print(f"[OK] Progetti processati: {projects_processed}")
        
        # Verifica finale: nessuna directory incoming dovrebbe contenere sessioni
        if not dry_run and total_sessions > 0:
            remaining = 0
            for project_dir in os.listdir(workspace_root):
                project_path = os.path.join(workspace_root, project_dir)
                if not os.path.isdir(project_path):
                    continue
                incoming_dir = os.path.join(project_path, 'incoming')
                if os.path.exists(incoming_dir):
                    for item in os.listdir(incoming_dir):
                        item_path = os.path.join(incoming_dir, item)
                        if os.path.isdir(item_path):
                            remaining += 1
            
            if remaining == 0:
                print("[OK] Verifica: tutte le sessioni sono state rimosse correttamente")
            else:
                print(f"[WARN] Verifica: {remaining} directory rimanenti in 'incoming/'")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Rimuove tutte le sessioni di upload senza toccare i repository gestiti'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mostra cosa verrebbe rimosso senza effettuare modifiche'
    )
    parser.add_argument(
        '--clear-history',
        action='store_true',
        help='Cancella anche i file history.json (opzionale)'
    )
    
    args = parser.parse_args()
    
    print("Pulizia sessioni di upload")
    print("=" * 60)
    print()
    
    if args.dry_run:
        print("[WARN] MODALITA DRY RUN: nessuna modifica verra effettuata")
        print()
    
    try:
        cleanup_all_sessions(dry_run=args.dry_run, clear_history=args.clear_history)
    except KeyboardInterrupt:
        print("\n[ERR] Interrotto dall'utente")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERR] Errore: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


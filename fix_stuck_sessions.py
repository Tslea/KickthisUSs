"""
Script per verificare e ripulire sessioni di upload bloccate in stato 'syncing'.
"""
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


def find_stuck_sessions(project_id=None):
    """Trova tutte le sessioni bloccate in 'syncing'."""
    instance_dir = Path(__file__).parent / 'instance'
    workspace_dir = instance_dir / 'workspace'
    
    if not workspace_dir.exists():
        print("❌ Directory workspace non trovata")
        return []
    
    stuck_sessions = []
    
    # Cerca in tutti i progetti o in uno specifico
    if project_id:
        project_dirs = [workspace_dir / str(project_id)]
    else:
        project_dirs = [d for d in workspace_dir.iterdir() if d.is_dir()]
    
    for project_dir in project_dirs:
        if not project_dir.exists():
            continue
            
        incoming_dir = project_dir / 'incoming'
        if not incoming_dir.exists():
            continue
        
        for session_dir in incoming_dir.iterdir():
            if not session_dir.is_dir():
                continue
            
            metadata_file = session_dir / 'metadata.json'
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                status = metadata.get('status', '')
                if status == 'syncing':
                    session_id = metadata.get('session_id', session_dir.name)
                    updated_at = metadata.get('updated_at') or metadata.get('created_at')
                    
                    # Calcola quanto tempo è passato
                    age = None
                    if updated_at:
                        try:
                            updated_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                            now = datetime.now(timezone.utc)
                            age = now - updated_time
                        except:
                            pass
                    
                    stuck_sessions.append({
                        'project_id': project_dir.name,
                        'session_id': session_id,
                        'status': status,
                        'updated_at': updated_at,
                        'age': age,
                        'age_minutes': age.total_seconds() / 60 if age else None,
                        'metadata_file': metadata_file,
                        'metadata': metadata
                    })
            except Exception as e:
                print(f"⚠️ Errore leggendo {metadata_file}: {e}")
    
    return stuck_sessions


def fix_stuck_session(session_info):
    """Marca una sessione bloccata come 'error'."""
    metadata_file = session_info['metadata_file']
    metadata = session_info['metadata']
    
    # Aggiorna lo stato
    metadata['status'] = 'error'
    metadata['error'] = 'Sync timeout - sessione bloccata recuperata manualmente'
    metadata['recovered_at'] = datetime.now(timezone.utc).isoformat()
    
    # Salva il file
    try:
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Errore salvando {metadata_file}: {e}")
        return False


def main():
    print("🔍 Cerco sessioni bloccate in 'syncing'...\n")
    
    stuck_sessions = find_stuck_sessions()
    
    if not stuck_sessions:
        print("✅ Nessuna sessione bloccata trovata!")
        return
    
    print(f"⚠️ Trovate {len(stuck_sessions)} sessioni bloccate:\n")
    
    for i, session in enumerate(stuck_sessions, 1):
        age_str = f"{session['age_minutes']:.1f} minuti" if session['age_minutes'] else "sconosciuto"
        print(f"{i}. Progetto {session['project_id']}")
        print(f"   Session: {session['session_id']}")
        print(f"   Status: {session['status']}")
        print(f"   Età: {age_str}")
        print(f"   Updated: {session['updated_at']}")
        print()
    
    # Chiedi conferma
    response = input("Vuoi marcare tutte queste sessioni come 'error'? [s/N]: ").strip().lower()
    
    if response in ['s', 'si', 'sì', 'y', 'yes']:
        fixed = 0
        for session in stuck_sessions:
            if fix_stuck_session(session):
                fixed += 1
                print(f"✅ Recuperata: {session['session_id']}")
            else:
                print(f"❌ Fallita: {session['session_id']}")
        
        print(f"\n✅ Recuperate {fixed}/{len(stuck_sessions)} sessioni")
        print("💡 Ricarica la pagina del progetto per vedere le modifiche")
    else:
        print("❌ Operazione annullata")


if __name__ == '__main__':
    main()

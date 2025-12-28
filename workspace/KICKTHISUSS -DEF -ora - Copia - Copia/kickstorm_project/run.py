# kickthisuss_project/run.py
import os
from dotenv import load_dotenv
from app import create_app, db

# Carica le variabili d'ambiente dal file .env
load_dotenv()

app = create_app()

def setup_database(app_instance):
    """
    Controlla se il database esiste e, in caso contrario, lo crea.
    """
    with app_instance.app_context():
        # Il percorso del database è definito nella configurazione dell'app
        db_path_str = app_instance.config.get('SQLALCHEMY_DATABASE_URI', '')
        
        # Semplice controllo per file-based-db come SQLite
        if db_path_str.startswith('sqlite:///'):
            db_filename = db_path_str.replace('sqlite:///', '')
            
            # Assicuriamoci che il percorso sia assoluto partendo dalla cartella 'instance'
            instance_path = app_instance.instance_path
            if not os.path.isabs(db_filename):
                db_filename = os.path.join(instance_path, db_filename)
            
            db_dir = os.path.dirname(db_filename)
            if not os.path.exists(db_dir):
                print(f"--- La directory per il database non esiste, la creo in: {db_dir} ---")
                os.makedirs(db_dir)

            if not os.path.exists(db_filename):
                print("--- Database non trovato. Avvio creazione... ---")
                try:
                    db.create_all()
                    print(">>> SUCCESS! Database e tabelle create correttamente.")
                except Exception as e:
                    print(f"!!! ERRORE durante la creazione del database: {e}")
            else:
                print("--- Database già esistente, avvio normale. ---")
        else:
            # Per altri tipi di DB (PostgreSQL, etc.) la logica potrebbe essere diversa
            print("--- Database non-SQLite, si presume esista già. ---")


# Esegui la funzione di setup prima di avviare l'app
setup_database(app)


if __name__ == '__main__':
    # Disabilita il reloader di Flask per evitare che setup_database venga chiamato due volte in debug mode
    app.run(debug=True, host='0.0.0.0', use_reloader=False)

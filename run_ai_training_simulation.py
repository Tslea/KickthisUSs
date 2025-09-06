# run_ai_training_simulation.py
import json
import os
from app import create_app, db
from app.models import TrainingData

def run_simulation():
    """
    Simula il processo di preparazione dei dati per il fine-tuning di un modello AI.
    Questo script legge i dati dalla tabella TrainingData, li formatta e li salva
    in un file JSON, pronti per un ipotetico processo di training.
    """
    print("--- Simulazione Training AI Avviata ---")

    # 1. Configura l'app Flask per accedere al contesto del database
    # Usiamo una configurazione che punta al database corretto
    # NOTA: Assicurati che 'instance/kickthisuss.db' sia il path corretto del tuo DB.
    # Potrebbe essere necessario creare una configurazione specifica per questo script.
    # Per semplicità, usiamo la DevelopmentConfig di default.
    app = create_app()
    with app.app_context():
        print("Contesto dell'applicazione caricato.")
        
        # 2. Recupera tutti i dati di training dal database
        training_records = TrainingData.query.all()
        if not training_records:
            print("Nessun record di training trovato nel database. Uscita.")
            return

        print(f"Trovati {len(training_records)} record di training.")

        # 3. Formatta i dati nel formato desiderato per il fine-tuning
        # Molti modelli di linguaggio si aspettano un formato "prompt" -> "completion"
        # o un formato di conversazione. Scegliamo un formato semplice:
        # {"prompt": "...", "completion": "..."}
        
        formatted_dataset = []
        for record in training_records:
            # Pulisci e formatta l'input (prompt)
            prompt = (
                f"Titolo del progetto: {record.input_data.get('project_pitch', '')}

"
                f"Descrizione del progetto: {record.input_data.get('project_description', '')}

"
                f"Titolo del task da risolvere: {record.input_data.get('task_title', '')}

"
                f"Descrizione del task: {record.input_data.get('task_description', '')}

"
                "SOLUZIONE APPROVATA:"
            )
            
            # Pulisci e formatta l'output (completion)
            completion = record.output_data.get('approved_solution_content', '')
            
            if not completion:
                continue # Salta i record senza una soluzione valida

            formatted_dataset.append({
                "prompt": prompt,
                "completion": f" {completion}" # Aggiungiamo uno spazio iniziale come da best practice
            })
        
        print(f"Formattati {len(formatted_dataset)} esempi validi per il training.")

        # 4. Mostra un esempio di dato formattato
        if formatted_dataset:
            print("
--- Esempio di dato formattato ---")
            print(json.dumps(formatted_dataset[0], indent=2, ensure_ascii=False))
            print("----------------------------------
")

        # 5. Salva il dataset formattato in un file JSON
        output_filename = "training_dataset.json"
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(formatted_dataset, f, indent=2, ensure_ascii=False)
            print(f"Dataset salvato con successo in '{os.path.abspath(output_filename)}'.")
        except Exception as e:
            print(f"Errore durante il salvataggio del file: {e}")

    print("--- Simulazione Training AI Completata ---")

if __name__ == '__main__':
    run_simulation()

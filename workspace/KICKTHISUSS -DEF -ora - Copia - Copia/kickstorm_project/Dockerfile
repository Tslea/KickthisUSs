# Usa un'immagine ufficiale Python come base
FROM python:3.12-slim

# Installa git e unzip per git sync
RUN apt-get update && apt-get install -y \
    git \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Imposta la directory di lavoro nel container
WORKDIR /app

# Copia il file delle dipendenze e installale
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del codice dell'applicazione
COPY . .

# Esponi la porta su cui Gunicorn sarà in ascolto
EXPOSE 8080

# Comando per avviare l'applicazione in produzione usando Gunicorn.
# Modificato per puntare direttamente all'application factory nel pacchetto 'app'
# Questo risolve l'ImportError e bypassa run.py in produzione.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "3", "app:create_app()"]

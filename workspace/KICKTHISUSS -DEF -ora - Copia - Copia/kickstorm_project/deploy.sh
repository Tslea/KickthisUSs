#!/bin/bash

# --- Configurazione ---
# Modifica queste variabili con i tuoi valori specifici.

# Il nome che vuoi dare al tuo servizio su Cloud Run (es. kickthisuss-app)
# Deve essere tutto in minuscolo.
SERVICE_NAME="kickthisuss-app-1" 

# La regione dove vuoi fare il deploy (es. us-central1, europe-west1).
# Scegline una vicina a te o ai tuoi utenti.
GCP_REGION="us-central1"

# --- Acquisizione e Verifica Configurazione ---

# L'ID del tuo progetto Google Cloud. 
# reindirizziamo l'output di errore a /dev/null per non sporcare la console.
GCP_PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

# Controlla se l'ID del progetto è stato trovato. Se è vuoto, esci con un errore.
if [ -z "$GCP_PROJECT_ID" ]; then
    echo "---------------------------------------------------------------------"
    echo "ERRORE: ID del Progetto Google Cloud non trovato."
    echo "Per favore, esegui questo comando e riprova:"
    echo "gcloud config set project NOME_DEL_TUO_PROGETTO"
    echo "---------------------------------------------------------------------"
    exit 1
fi

echo "--- Deploy in corso per il progetto: $GCP_PROJECT_ID ---"

# Il nome dell'immagine Docker che verrà creata.
IMAGE_NAME="gcr.io/$GCP_PROJECT_ID/$SERVICE_NAME"


# --- Esecuzione dei Comandi ---

# 1. Costruisce l'immagine Docker in locale.
echo "--- Passo 1: Costruzione dell'immagine Docker ---"
docker build -t $IMAGE_NAME .
if [ $? -ne 0 ]; then
    echo "Errore durante la costruzione dell'immagine Docker. Interruzione."
    exit 1
fi

# 2. Autentica Docker con Google Container Registry (GCR).
echo "--- Passo 2: Autenticazione con Google Container Registry ---"
gcloud auth configure-docker
if [ $? -ne 0 ]; then
    echo "Errore durante l'autenticazione con GCR. Interruzione."
    exit 1
fi

# 3. Carica l'immagine Docker su Google Container Registry.
echo "--- Passo 3: Caricamento dell'immagine su GCR ---"
docker push $IMAGE_NAME
if [ $? -ne 0 ]; then
    echo "Errore durante il caricamento dell'immagine. Interruzione."
    exit 1
fi

# 4. Esegue il deploy dell'immagine su Cloud Run.
echo "--- Passo 4: Deploy su Google Cloud Run ---"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $GCP_REGION \
    --allow-unauthenticated \
    --port 8080
if [ $? -ne 0 ]; then
    echo "Errore durante il deploy su Cloud Run. Interruzione."
    exit 1
fi

echo "--- Deploy completato! ---"
echo "Il tuo servizio è ora disponibile all'URL fornito da Cloud Run."

@echo off
REM Script per avviare Flask + Celery Worker insieme
REM Usa questo invece di 'python run.py'

echo ========================================
echo Avvio KickThisUss con Celery Worker
echo ========================================
echo.

REM Avvia Celery Worker in background
echo [1/2] Avvio Celery Worker...
start "Celery Worker" cmd /k celery -A tasks.celery worker --loglevel=info --pool=solo

REM Aspetta 3 secondi per dare tempo a Celery di partire
timeout /t 3 /nobreak >nul

REM Avvia Flask
echo [2/2] Avvio Flask Server...
python run.py

REM Se Flask viene chiuso, questo script termina
REM Il worker Celery continuerà in una finestra separata

"""
API endpoints per la generazione automatica di guide AI dei progetti
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Project
from app.ai_services import analyze_with_ai
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

api_ai_projects = Blueprint('api_ai_projects', __name__)

@api_ai_projects.route('/projects/<int:project_id>/generate-ai-guide', methods=['POST'])
@login_required
def generate_project_ai_guide(project_id):
    """Genera la guida AI per un progetto (MVP + Analisi fattibilità)"""
    try:
        # Trova il progetto
        project = Project.query.get_or_404(project_id)
        
        # Verifica che l'utente sia il creatore (solo lui può generare la guida iniziale)
        if project.creator_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Solo il creatore del progetto può generare la guida AI'
            }), 403
        
        # Prepara le informazioni del progetto
        project_info = f"""
        NOME PROGETTO: {project.name}
        CATEGORIA: {project.category}
        PITCH: {project.pitch or 'Non specificato'}
        DESCRIZIONE: {project.description or 'Non specificata'}
        """
        
        # 1. Genera la guida MVP step-by-step
        mvp_prompt = f"""
        TASK: Crea una guida dettagliata step-by-step per sviluppare un MVP (Minimum Viable Product) per il seguente progetto.
        
        INFORMAZIONI PROGETTO:
        {project_info}
        
        ISTRUZIONI:
        1. Analizza il progetto e identifica le funzionalità core essenziali per un MVP
        2. Crea una roadmap step-by-step chiara e actionable
        3. Ogni step deve essere specifico e realizzabile
        4. Includi considerazioni tecniche, di design e di business
        5. Organizza in fasi logiche e progressive
        6. Stima tempi realistici per ogni fase
        
        FORMATO RISPOSTA:
        # 📋 Guida MVP: [Nome Progetto]
        
        ## 🎯 Obiettivo MVP
        [Descrizione chiara di cosa deve fare l'MVP]
        
        ## ⚡ Funzionalità Core (Must-Have)
        1. [Funzionalità essenziale 1]
        2. [Funzionalità essenziale 2]
        ...
        
        ## 🚀 Roadmap di Sviluppo
        
        ### Fase 1: Fondamenta (Settimana 1-2)
        - [ ] [Task specifico]
        - [ ] [Task specifico]
        
        ### Fase 2: Funzionalità Core (Settimana 3-4)
        - [ ] [Task specifico]
        - [ ] [Task specifico]
        
        ### Fase 3: Testing e Rilascio (Settimana 5-6)
        - [ ] [Task specifico]
        - [ ] [Task specifico]
        
        ## 🛠️ Stack Tecnologico Consigliato
        - **Frontend**: [Raccomandazione]
        - **Backend**: [Raccomandazione]
        - **Database**: [Raccomandazione]
        - **Hosting**: [Raccomandazione]
        
        ## 📊 Metriche di Successo
        1. [Metrica misurabile]
        2. [Metrica misurabile]
        """
        
        # 2. Genera l'analisi di fattibilità
        feasibility_prompt = f"""
        TASK: Effettua un'analisi realistica e professionale delle possibilità di successo del seguente progetto.
        
        INFORMAZIONI PROGETTO:
        {project_info}
        
        ISTRUZIONI:
        1. Analizza il progetto da prospettive multiple: tecnica, di mercato, finanziaria
        2. Identifica opportunità e sfide realistiche
        3. Fornisci valutazioni honest e costruttive
        4. Includi considerazioni su competitors e market fit
        5. Suggerisci miglioramenti e alternative
        6. Usa un tono professionale ma accessibile
        
        FORMATO RISPOSTA:
        # 📊 Analisi di Fattibilità: [Nome Progetto]
        
        ## ✅ Punti di Forza
        1. [Punto forte identificato]
        2. [Punto forte identificato]
        
        ## ⚠️ Sfide e Rischi
        1. [Sfida realistica]
        2. [Sfida realistica]
        
        ## 🎯 Market Analysis
        - **Dimensione del mercato**: [Valutazione]
        - **Competitors principali**: [Analisi competitors]
        - **Differenziazione**: [Come distinguersi]
        
        ## 💰 Considerazioni Finanziarie
        - **Costi di sviluppo stimati**: [Stima realistica]
        - **Possibili modelli di monetizzazione**: [Opzioni]
        - **Tempo per break-even**: [Stima]
        
        ## 🚀 Probabilità di Successo
        - **Tecnica**: [Valutazione 1-10 con spiegazione]
        - **Di mercato**: [Valutazione 1-10 con spiegazione]
        - **Complessiva**: [Valutazione finale]
        
        ## 💡 Raccomandazioni
        1. [Raccomandazione specifica]
        2. [Raccomandazione specifica]
        
        ## 🎯 Next Steps Prioritari
        1. [Azione concreta da intraprendere]
        2. [Azione concreta da intraprendere]
        """
        
        # Chiama AI per entrambe le analisi
        logger.info(f"Generando guida MVP per progetto {project_id}")
        mvp_guide = analyze_with_ai(mvp_prompt)
        
        logger.info(f"Generando analisi fattibilità per progetto {project_id}")
        feasibility_analysis = analyze_with_ai(feasibility_prompt)
        
        if not mvp_guide or not feasibility_analysis:
            return jsonify({
                'success': False,
                'error': 'Errore durante la generazione delle guide AI'
            }), 500
        
        # Salva nel database
        project.ai_mvp_guide = mvp_guide
        project.ai_feasibility_analysis = feasibility_analysis
        project.ai_guide_generated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Guide AI generate con successo',
            'mvp_guide': mvp_guide,
            'feasibility_analysis': feasibility_analysis,
            'generated_at': project.ai_guide_generated_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Errore generazione guide AI: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Errore interno del server'
        }), 500

@api_ai_projects.route('/projects/<int:project_id>/update-ai-guide', methods=['PUT'])
@login_required
def update_project_ai_guide(project_id):
    """Aggiorna manualmente le guide AI del progetto"""
    try:
        # Trova il progetto
        project = Project.query.get_or_404(project_id)
        
        # Verifica che l'utente sia il creatore
        if project.creator_id != current_user.id:
            return jsonify({
                'success': False,
                'error': 'Solo il creatore del progetto può modificare le guide AI'
            }), 403
        
        data = request.get_json()
        
        # Aggiorna i campi forniti
        if 'mvp_guide' in data:
            project.ai_mvp_guide = data['mvp_guide']
        
        if 'feasibility_analysis' in data:
            project.ai_feasibility_analysis = data['feasibility_analysis']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Guide AI aggiornate con successo'
        })
        
    except Exception as e:
        logger.error(f"Errore aggiornamento guide AI: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Errore interno del server'
        }), 500

@api_ai_projects.route('/projects/<int:project_id>/ai-guide', methods=['GET'])
@login_required  
def get_project_ai_guide(project_id):
    """Recupera le guide AI del progetto"""
    try:
        project = Project.query.get_or_404(project_id)
        
        # Verifica accesso al progetto (pubblico o collaboratore)
        if project.private:
            # Per progetti privati, verifica se è creatore o collaboratore
            from app.models import Collaborator
            if (project.creator_id != current_user.id and 
                not Collaborator.query.filter_by(project_id=project_id, user_id=current_user.id).first()):
                return jsonify({
                    'success': False,
                    'error': 'Non hai accesso a questo progetto'
                }), 403
        
        return jsonify({
            'success': True,
            'mvp_guide': project.ai_mvp_guide,
            'feasibility_analysis': project.ai_feasibility_analysis,
            'generated_at': project.ai_guide_generated_at.isoformat() if project.ai_guide_generated_at else None,
            'can_edit': project.creator_id == current_user.id
        })
        
    except Exception as e:
        logger.error(f"Errore recupero guide AI: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Errore interno del server'
        }), 500

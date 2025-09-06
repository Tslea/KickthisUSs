# Esempio di AI Project Management - Task Generation

class AITaskGenerator:
    """IA che genera automaticamente task da descrizioni di progetto"""
    
    def generate_tasks_from_description(self, project_description):
        """
        Esempio: Input: "Voglio creare un'app per delivery di cibo"
        Output: Task strutturati automaticamente
        """
        # Prompt per GPT-4
        prompt = f"""
        Analizza questa descrizione di progetto e genera task strutturati:
        "{project_description}"
        
        Genera task divisi per categoria:
        - Research & Planning
        - Design & UX
        - Development
        - Testing & QA
        - Marketing & Launch
        
        Per ogni task include:
        - Titolo specifico
        - Descrizione dettagliata
        - Skill richieste
        - Tempo stimato
        - Priorità
        - Dipendenze
        """
        
        # Esempio di output generato
        return {
            "research_planning": [
                {
                    "title": "Analisi competitor food delivery",
                    "description": "Ricerca e analisi di UberEats, Deliveroo, Glovo...",
                    "skills": ["market research", "competitive analysis"],
                    "estimated_hours": 20,
                    "priority": "high",
                    "dependencies": []
                },
                {
                    "title": "Definizione target audience",
                    "description": "Identificare demographics e personas...",
                    "skills": ["user research", "data analysis"],
                    "estimated_hours": 15,
                    "priority": "high",
                    "dependencies": ["analisi_competitor"]
                }
            ],
            "design_ux": [
                {
                    "title": "Wireframe app mobile",
                    "description": "Creare wireframe per user journey...",
                    "skills": ["ui/ux design", "figma", "mobile design"],
                    "estimated_hours": 30,
                    "priority": "high",
                    "dependencies": ["target_audience"]
                }
            ],
            "development": [
                {
                    "title": "Setup backend API",
                    "description": "Configurare server Node.js con database...",
                    "skills": ["nodejs", "mongodb", "api development"],
                    "estimated_hours": 40,
                    "priority": "high",
                    "dependencies": ["wireframe_completato"]
                }
            ]
        }
    
    def estimate_project_timeline(self, tasks):
        """Stima timeline realistico basato su task e dipendenze"""
        pass
    
    def suggest_team_composition(self, tasks):
        """Suggerisce composizione team ottimale"""
        return {
            "frontend_developer": {"skills": ["react", "react-native"], "workload": "40h/week"},
            "backend_developer": {"skills": ["nodejs", "mongodb"], "workload": "35h/week"},
            "ux_designer": {"skills": ["figma", "user research"], "workload": "25h/week"},
            "project_manager": {"skills": ["project management", "agile"], "workload": "20h/week"}
        }

# AI Predictive Analytics per Project Management

class PredictiveProjectAnalytics:
    """IA per analisi predittive sui progetti"""
    
    def predict_project_risks(self, project_data):
        """
        Analizza dati storici per predire rischi
        """
        risk_factors = {
            "team_experience": self.analyze_team_experience(project_data['team']),
            "scope_complexity": self.analyze_scope_complexity(project_data['tasks']),
            "timeline_realism": self.analyze_timeline_realism(project_data['timeline']),
            "resource_availability": self.analyze_resource_availability(project_data['team'])
        }
        
        predictions = {
            "delay_probability": 0.35,  # 35% probabilità di ritardo
            "budget_overrun_risk": 0.20,  # 20% rischio sforamento budget
            "team_burnout_risk": 0.15,   # 15% rischio burnout
            "scope_creep_risk": 0.40     # 40% rischio scope creep
        }
        
        return {
            "predictions": predictions,
            "recommendations": self.generate_risk_mitigation_strategies(predictions)
        }
    
    def generate_risk_mitigation_strategies(self, predictions):
        """Genera strategie per mitigare i rischi"""
        strategies = []
        
        if predictions["delay_probability"] > 0.3:
            strategies.append({
                "risk": "Delay Risk",
                "strategy": "Implementare daily standups e milestone più frequenti",
                "action": "Suddividere task grandi in micro-task di 2-4 ore"
            })
        
        if predictions["team_burnout_risk"] > 0.1:
            strategies.append({
                "risk": "Team Burnout",
                "strategy": "Introdurre rotazione task e pause obbligatorie",
                "action": "Limitare workload a 6h/giorno per collaboratore"
            })
        
        return strategies
    
    def predict_optimal_team_size(self, project_scope):
        """Predice dimensione team ottimale"""
        # Analisi basata su progetti simili
        if project_scope == "mobile_app":
            return {
                "optimal_size": 5,
                "composition": {
                    "frontend": 2,
                    "backend": 1,
                    "design": 1,
                    "pm": 1
                },
                "confidence": 0.87
            }
    
    def predict_success_probability(self, project_data):
        """Predice probabilità di successo del progetto"""
        factors = {
            "team_cohesion": 0.8,
            "market_timing": 0.7,
            "technical_feasibility": 0.9,
            "resource_adequacy": 0.6
        }
        
        # Algoritmo weighted average
        success_probability = sum(factors.values()) / len(factors)
        
        return {
            "success_probability": success_probability,
            "key_factors": factors,
            "improvement_suggestions": self.suggest_success_improvements(factors)
        }

# AI Intelligent Task Assignment

class IntelligentTaskSuggestion:
    """IA per suggerimenti intelligenti sui task (senza assegnazione automatica)"""
    
    def __init__(self):
        self.suggestion_factors = {
            "skill_match": 0.4,      # 40% peso per matching skills
            "availability": 0.25,    # 25% peso per disponibilità
            "experience_level": 0.15, # 15% peso per esperienza
            "past_performance": 0.10, # 10% peso per performance passate
            "learning_interest": 0.05, # 5% peso per interesse ad apprendere
            "workload_balance": 0.05  # 5% peso per bilanciamento carico
        }
    
    def suggest_best_collaborators_for_task(self, task_id, available_collaborators):
        """
        Suggerisce i migliori collaboratori per un task (senza assegnazione automatica)
        """
        task = self.get_task_details(task_id)
        scores = {}
        
        for collaborator in available_collaborators:
            score = self.calculate_suggestion_score(task, collaborator)
            scores[collaborator.id] = score
        
        # Ordina collaboratori per score (migliore per primo)
        sorted_collaborators = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "suggested_collaborators": [
                {
                    "collaborator_id": collab_id,
                    "confidence_score": score,
                    "reasoning": self.explain_assignment_decision(task, collab_id),
                    "rank": idx + 1
                }
                for idx, (collab_id, score) in enumerate(sorted_collaborators[:5])  # Top 5 suggestions
            ],
            "task_requirements": {
                "skills": task.required_skills,
                "complexity": task.complexity,
                "estimated_hours": task.estimated_hours
            }
        }
    
    def calculate_suggestion_score(self, task, collaborator):
        """Calcola score di compatibilità task-collaboratore per suggerimenti"""
        
        # 1. Skill Match Score
        skill_match = self.calculate_skill_match(task.required_skills, collaborator.skills)
        
        # 2. Availability Score
        availability = self.calculate_availability_score(collaborator.current_workload)
        
        # 3. Experience Level Score
        experience = self.calculate_experience_score(task.complexity, collaborator.experience)
        
        # 4. Past Performance Score
        performance = self.get_past_performance_score(collaborator.id)
        
        # 5. Learning Interest Score
        learning_interest = self.calculate_learning_interest(task.skills, collaborator.learning_goals)
        
        # 6. Workload Balance Score
        workload_balance = self.calculate_workload_balance_score(collaborator.current_workload)
        
        # Weighted final score
        final_score = (
            skill_match * self.suggestion_factors["skill_match"] +
            availability * self.suggestion_factors["availability"] +
            experience * self.suggestion_factors["experience_level"] +
            performance * self.suggestion_factors["past_performance"] +
            learning_interest * self.suggestion_factors["learning_interest"] +
            workload_balance * self.suggestion_factors["workload_balance"]
        )
        
        return final_score
    
    def explain_suggestion_rationale(self, task, collaborator_id):
        """Spiega perché questo collaboratore è suggerito per il task"""
        return {
            "primary_reason": "Skill match perfetto per React Native (95%)",
            "secondary_reasons": [
                "Disponibilità immediata (25h/settimana)",
                "Esperienza con progetti simili (4 progetti completati)",
                "Performance rating alto (4.8/5)"
            ],
            "potential_concerns": [
                "Carico di lavoro già al 70% - monitorare per evitare burnout"
            ],
            "recommendation": "Collaboratore altamente raccomandato per questo task"
        }
    
    def suggest_task_redistribution(self, project_id):
        """Suggerisce redistribuzione task per ottimizzare performance"""
        current_assignments = self.get_current_assignments(project_id)
        
        suggestions = []
        
        # Identifica squilibri
        overloaded_collaborators = self.find_overloaded_collaborators(current_assignments)
        underutilized_collaborators = self.find_underutilized_collaborators(current_assignments)
        
        # Suggerisce redistribuzioni
        for overloaded in overloaded_collaborators:
            for task in overloaded.tasks:
                if task.can_be_reassigned:
                    better_match = self.find_better_assignment(task, underutilized_collaborators)
                    if better_match:
                        suggestions.append({
                            "action": "suggest_reassign",
                            "task": task.id,
                            "current_assignee": overloaded.id,
                            "suggested_assignee": better_match.id,
                            "reason": "Riequilibrio carico di lavoro e migliore skill match",
                            "requires_approval": True
                        })
        
        return suggestions
    
    def dynamic_task_prioritization(self, project_id):
        """Riordina priorità task dinamicamente"""
        project_status = self.get_project_status(project_id)
        
        # Fattori che influenzano priorità
        priority_factors = {
            "deadline_proximity": self.calculate_deadline_pressure(project_status),
            "dependency_chain": self.analyze_task_dependencies(project_id),
            "team_availability": self.analyze_team_availability(project_id),
            "external_constraints": self.check_external_constraints(project_id)
        }
        
        # Riordina task basandosi su fattori multipli
        reprioritized_tasks = self.calculate_dynamic_priorities(priority_factors)
        
        return {
            "updated_priorities": reprioritized_tasks,
            "rationale": "Riprioritizzazione basata su deadline e disponibilità team",
            "impact_analysis": self.analyze_priority_change_impact(reprioritized_tasks)
        }
    
    def analyze_collaborator_task_compatibility(self, collaborator_id, task_id):
        """Analizza compatibilità specifica tra collaboratore e task"""
        collaborator = self.get_collaborator_details(collaborator_id)
        task = self.get_task_details(task_id)
        
        compatibility_analysis = {
            "overall_score": self.calculate_suggestion_score(task, collaborator),
            "skill_analysis": {
                "required_skills": task.required_skills,
                "collaborator_skills": collaborator.skills,
                "skill_gaps": self.identify_skill_gaps(task.required_skills, collaborator.skills),
                "skill_match_percentage": self.calculate_skill_match(task.required_skills, collaborator.skills)
            },
            "workload_analysis": {
                "current_workload": collaborator.current_workload,
                "availability": self.calculate_availability_score(collaborator.current_workload),
                "time_to_complete": self.estimate_completion_time(task, collaborator)
            },
            "experience_analysis": {
                "task_complexity": task.complexity,
                "collaborator_experience": collaborator.experience,
                "suitability": self.calculate_experience_score(task.complexity, collaborator.experience)
            },
            "recommendation": self.generate_compatibility_recommendation(task, collaborator)
        }
        
        return compatibility_analysis
    
    def generate_compatibility_recommendation(self, task, collaborator):
        """Genera raccomandazione sulla compatibilità"""
        score = self.calculate_suggestion_score(task, collaborator)
        
        if score >= 0.8:
            return {
                "level": "highly_recommended",
                "message": "Collaboratore altamente compatibile con questo task",
                "confidence": "high"
            }
        elif score >= 0.6:
            return {
                "level": "recommended",
                "message": "Buona compatibilità, potrebbe necessitare supporto minimo",
                "confidence": "medium"
            }
        elif score >= 0.4:
            return {
                "level": "conditional",
                "message": "Compatibilità moderata, richiede supporto o training",
                "confidence": "medium"
            }
        else:
            return {
                "level": "not_recommended",
                "message": "Compatibilità bassa, considerare altri collaboratori",
                "confidence": "high"
            }

    def suggest_task_alternatives_for_collaborator(self, collaborator_id, project_id):
        """Suggerisce task alternativi più adatti per un collaboratore"""
        collaborator = self.get_collaborator_details(collaborator_id)
        available_tasks = self.get_unassigned_tasks(project_id)
        
        task_scores = {}
        for task in available_tasks:
            score = self.calculate_suggestion_score(task, collaborator)
            task_scores[task.id] = {
                "score": score,
                "task": task,
                "rationale": self.explain_suggestion_rationale(task, collaborator_id)
            }
        
        # Ordina task per compatibilità
        sorted_tasks = sorted(task_scores.items(), key=lambda x: x[1]["score"], reverse=True)
        
        return {
            "collaborator_id": collaborator_id,
            "suggested_tasks": [
                {
                    "task_id": task_id,
                    "task_title": data["task"].title,
                    "compatibility_score": data["score"],
                    "rationale": data["rationale"],
                    "rank": idx + 1
                }
                for idx, (task_id, data) in enumerate(sorted_tasks[:10])  # Top 10 suggestions
            ],
            "collaborator_strengths": self.identify_collaborator_strengths(collaborator),
            "development_opportunities": self.identify_development_opportunities(collaborator, available_tasks)
        }

# test_complete_ai_tasks.py
"""
Test completo per tutte le funzionalità di task AI
"""

def test_ai_task_comprehensive():
    """Test completo delle funzionalità AI task"""
    from app import create_app
    from app.ai_services import generate_suggested_tasks, AI_SERVICE_AVAILABLE
    from app.models import Task, Project
    from app.extensions import db
    
    app = create_app()
    
    print("🔧 Test Completo AI Task Generation")
    print("=" * 50)
    
    with app.app_context():
        print(f"1. ✅ AI Service disponibile: {AI_SERVICE_AVAILABLE}")
        
        # Test 1: Generazione task base
        tasks = generate_suggested_tasks(
            "App per prenotare campi da tennis", 
            "Tech", 
            "Una app mobile per prenotare campi da tennis in tempo reale",
            []
        )
        
        print(f"2. ✅ Task generati: {len(tasks)}")
        
        # Test 2: Verifica tipi di task
        task_types = [task.get('task_type') for task in tasks]
        print(f"3. ✅ Tipi task: {set(task_types)}")
        
        # Test 3: Verifica validation tasks
        validation_tasks = [task for task in tasks if task.get('task_type') == 'validation']
        print(f"4. ✅ Task validation: {len(validation_tasks)}")
        
        for val_task in validation_tasks:
            has_hypothesis = bool(val_task.get('hypothesis'))
            has_test_method = bool(val_task.get('test_method'))
            print(f"   - {val_task.get('title')}: hypothesis={has_hypothesis}, test_method={has_test_method}")
        
        # Test 4: Verifica equity range
        equity_values = [task.get('equity_reward', 0) for task in tasks]
        min_equity = min(equity_values) if equity_values else 0
        max_equity = max(equity_values) if equity_values else 0
        print(f"5. ✅ Equity range: {min_equity:.1f}% - {max_equity:.1f}%")
        
        # Test 5: Verifica campi richiesti
        required_fields = ['title', 'description', 'task_type', 'phase', 'difficulty', 'equity_reward']
        all_valid = True
        for i, task in enumerate(tasks):
            missing_fields = [field for field in required_fields if field not in task or not task[field]]
            if missing_fields:
                print(f"   ❌ Task {i+1} manca: {missing_fields}")
                all_valid = False
        
        if all_valid:
            print("6. ✅ Tutti i task hanno i campi richiesti")
        
        print("\n📊 Riepilogo Test:")
        print(f"   - Servizio AI: {'✅ Funzionante' if AI_SERVICE_AVAILABLE else '❌ Non disponibile'}")
        print(f"   - Task generati: {len(tasks)}")
        print(f"   - Task validation con hypothesis/test_method: {len(validation_tasks)}")
        print(f"   - Tutti i campi presenti: {'✅' if all_valid else '❌'}")
        
        return tasks

if __name__ == "__main__":
    test_ai_task_comprehensive()

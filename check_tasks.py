#!/usr/bin/env python3
"""Script per verificare i task nel database"""
from app import create_app, db
from app.models import Task

app = create_app()

with app.app_context():
    print("\n=== VERIFICA TASK NEL DATABASE ===\n")
    
    # Conta tutti i task
    total_tasks = Task.query.count()
    print(f"Totale task: {total_tasks}")
    
    # Conta task per is_private
    private_true = Task.query.filter_by(is_private=True).count()
    private_false = Task.query.filter_by(is_private=False).count()
    private_null = Task.query.filter(Task.is_private.is_(None)).count()
    
    print(f"\nTask per is_private:")
    print(f"  is_private=True:  {private_true}")
    print(f"  is_private=False: {private_false}")
    print(f"  is_private=NULL:  {private_null}")
    
    # Conta task per status
    print(f"\nTask per status:")
    statuses = db.session.query(Task.status, db.func.count(Task.id)).group_by(Task.status).all()
    for status, count in statuses:
        print(f"  {status}: {count}")
    
    # Mostra primi 5 task
    print(f"\n=== PRIMI 5 TASK ===")
    tasks = Task.query.limit(5).all()
    for t in tasks:
        print(f"\nTask #{t.id}:")
        print(f"  Title: {t.title}")
        print(f"  Status: {t.status}")
        print(f"  is_private: {t.is_private}")
        print(f"  Project ID: {t.project_id}")
    
    # Conta task che matchano il filtro
    print(f"\n=== TASK CHE MATCHANO IL FILTRO (is_private=False AND status IN approved/completed) ===")
    matching = Task.query.filter_by(is_private=False).filter(
        Task.status.in_(['approved', 'completed'])
    ).count()
    print(f"Task che matchano: {matching}")
    
    if matching > 0:
        print("\nEsempi di task che matchano:")
        examples = Task.query.filter_by(is_private=False).filter(
            Task.status.in_(['approved', 'completed'])
        ).limit(3).all()
        for t in examples:
            print(f"  - Task #{t.id}: {t.title} (status={t.status})")

# app/routes_users.py
from flask import Blueprint, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from .models import User, Collaborator, Project, Solution, Task, Vote, ALLOWED_TASK_TYPES
from .forms import UpdateProfileForm
from .extensions import db
from sqlalchemy.orm import joinedload
from werkzeug.utils import secure_filename
from PIL import Image
import os
from datetime import datetime

users_bp = Blueprint('users', __name__, template_folder='templates')

@users_bp.route('/profile/<username>')
@login_required
def user_profile(username):
    """Mostra la pagina del profilo di un utente con i suoi progetti."""
    # Recupera l'utente all'inizio
    user = User.query.filter_by(username=username).first_or_404()
    
    # Progetti creati dall'utente
    projects_created = Project.query.filter_by(creator_id=user.id).order_by(Project.created_at.desc()).all()

    # Collaborazioni e progetti a cui ha contribuito
    collaborations = Collaborator.query.options(joinedload(Collaborator.project)).filter_by(user_id=user.id).all()
    projects_contributed = [collab.project for collab in collaborations if collab.project]

    # Task completati: quelli dove l'utente ha una soluzione approvata
    approved_solutions = Solution.query.filter_by(submitted_by_user_id=user.id, is_approved=True).all()
    completed_task_ids = {sol.task_id for sol in approved_solutions}
    completed_tasks = Task.query.filter(Task.id.in_(completed_task_ids)).all() if completed_task_ids else []

    # Nuove metriche aggiuntive
    total_solutions = Solution.query.filter_by(submitted_by_user_id=user.id).count()
    total_tasks_created = Task.query.filter_by(creator_id=user.id).count()

    # Conta task per categoria
    task_type_counts = {k: 0 for k in ALLOWED_TASK_TYPES.keys()}
    for t in completed_tasks:
        if t.task_type in task_type_counts:
            task_type_counts[t.task_type] += 1

    # Equity totale guadagnata
    total_equity = sum(collab.equity_share for collab in collaborations)
    
    # 🎯 EQUITY DETAILED BREAKDOWN using ProjectEquity system
    from .services.equity_service import EquityService
    equity_service = EquityService()
    equity_summary = equity_service.calculate_user_total_equity(user)

    # Soluzioni approvate
    num_approved_solutions = len(approved_solutions)

    # Progetti a cui ha contribuito
    num_projects_contributed = len(projects_contributed)

    # Task completati
    num_tasks_completed = len(completed_tasks)

    # Sistema di reputazione e skill points (esempio: +10 per ogni task completato, +20 per ogni soluzione approvata, +10 per ogni voto positivo)
    skill_points = {k: 0 for k in ALLOWED_TASK_TYPES.keys()}
    for t in completed_tasks:
        if t.task_type in skill_points:
            skill_points[t.task_type] += 10
    reputation_points = num_tasks_completed * 10 + num_approved_solutions * 20

    # Voti positivi ricevuti sulle soluzioni approvate
    positive_votes = Vote.query.filter(Vote.solution_id.in_([sol.id for sol in approved_solutions])).count() if approved_solutions else 0
    reputation_points += positive_votes * 10

    # Voti positivi ricevuti per ogni categoria
    positive_votes_by_category = {k: 0 for k in ALLOWED_TASK_TYPES.keys()}
    for t in completed_tasks:
        if t.task_type in positive_votes_by_category:
            sol = Solution.query.filter_by(task_id=t.id, submitted_by_user_id=user.id, is_approved=True).first()
            if sol:
                votes = Vote.query.filter_by(solution_id=sol.id).count()
                positive_votes_by_category[t.task_type] += votes

    # Skill points dettagliati per categoria (curriculum)
    curriculum_skills = []
    for cat, label in ALLOWED_TASK_TYPES.items():
        skill = {
            'category': label,
            'tasks_completed': task_type_counts.get(cat, 0),
            'skill_points': skill_points.get(cat, 0),
            'positive_votes': positive_votes_by_category.get(cat, 0)
        }
        curriculum_skills.append(skill)

    return render_template(
        'user_profile.html',
        user=user,
        projects_created=projects_created,
        projects_contributed=projects_contributed,
        collaborations=collaborations,
        num_projects_contributed=num_projects_contributed,
        num_tasks_completed=num_tasks_completed,
        task_type_counts=task_type_counts,
        num_approved_solutions=num_approved_solutions,
        total_equity=total_equity,
        reputation_points=reputation_points,
        skill_points=skill_points,
        curriculum_skills=curriculum_skills,
        total_solutions=total_solutions,
        total_tasks_created=total_tasks_created,
        ALLOWED_TASK_TYPES=ALLOWED_TASK_TYPES,
        equity_summary=equity_summary
    )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg', 'png', 'gif'}

def save_profile_image(form_picture, username):
    """Salva l'immagine del profilo in modo sicuro"""
    if not form_picture:
        return None
    
    # Genera un nome file sicuro
    filename = secure_filename(form_picture.filename)
    name, ext = os.path.splitext(filename)
    
    # Crea un nome file unico basato su username e timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    picture_filename = f"{username}_{timestamp}{ext}"
    
    # Percorso per salvare l'immagine
    upload_folder = os.path.join(current_app.root_path, 'static', 'profile_images')
    os.makedirs(upload_folder, exist_ok=True)
    picture_path = os.path.join(upload_folder, picture_filename)
    
    # Ridimensiona l'immagine per ottimizzare le prestazioni
    try:
        image = Image.open(form_picture)
        image.thumbnail((300, 300))  # Ridimensiona a max 300x300
        image.save(picture_path, optimize=True, quality=85)
        
        # Ritorna il percorso relativo per il database
        return f"profile_images/{picture_filename}"
    except Exception as e:
        print(f"Errore nel processare l'immagine: {e}")
        return None

@users_bp.route('/profile/update', methods=['GET', 'POST'])
@login_required
def update_profile():
    form = UpdateProfileForm()
    
    if form.validate_on_submit():
        if form.profile_image.data:
            # Elimina la vecchia immagine se esiste
            if current_user.profile_image_url:
                old_image_path = os.path.join(current_app.root_path, 'static', current_user.profile_image_url)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            # Salva la nuova immagine
            image_filename = save_profile_image(form.profile_image.data, current_user.username)
            if image_filename:
                current_user.profile_image_url = image_filename
                db.session.commit()
                flash('Immagine profilo aggiornata con successo!', 'success')
            else:
                flash('Errore nell\'aggiornamento dell\'immagine profilo.', 'error')
        
        return redirect(url_for('users.user_profile', username=current_user.username))
    
    return render_template('users/update_profile.html', form=form)

@users_bp.route('/account/delete', methods=['GET', 'POST'])
@login_required
def delete_account():
    """
    GDPR Compliant Account Deletion Endpoint
    Allows users to permanently delete their account and all associated data
    """
    from flask import request
    
    if request.method == 'POST':
        # Double confirmation check
        confirmation = request.form.get('confirmation')
        username_check = request.form.get('username_check')
        
        if confirmation != 'DELETE' or username_check != current_user.username:
            flash('Conferma non valida. Inserisci correttamente i dati richiesti.', 'error')
            return render_template('users/delete_account.html')
        
        # Log the deletion for audit purposes
        current_app.logger.warning(f"User {current_user.username} (ID: {current_user.id}) requested account deletion")
        
        user_email = current_user.email
        user_id = current_user.id
        username = current_user.username
        
        try:
            # 1. Delete user's solutions
            Solution.query.filter_by(submitted_by_user_id=user_id).delete()
            
            # 2. Delete user's votes
            Vote.query.filter_by(user_id=user_id).delete()
            
            # 3. Delete collaborations (but keep the projects)
            Collaborator.query.filter_by(user_id=user_id).delete()
            
            # 4. Delete equity history records (as user)
            from .models import EquityHistory
            EquityHistory.query.filter_by(user_id=user_id).delete()
            
            # 5. Delete project equity allocations
            from .models import ProjectEquity
            ProjectEquity.query.filter_by(user_id=user_id).delete()
            
            # 6. Handle user's created projects - reassign or delete
            projects_created = Project.query.filter_by(creator_id=user_id).all()
            for project in projects_created:
                # If project has other collaborators, assign to first collaborator
                collaborators = Collaborator.query.filter_by(project_id=project.id).first()
                if collaborators:
                    project.creator_id = collaborators.user_id
                else:
                    # Delete project and its tasks if no collaborators
                    Task.query.filter_by(project_id=project.id).delete()
                    db.session.delete(project)
            
            # 7. Delete user's created tasks
            Task.query.filter_by(creator_id=user_id).delete()
            
            # 8. Delete notifications
            from .models import Notification
            Notification.query.filter_by(user_id=user_id).delete()
            
            # 9. Delete profile image if exists
            if current_user.profile_image_url:
                try:
                    old_image_path = os.path.join(current_app.root_path, 'static', current_user.profile_image_url)
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                except Exception as e:
                    current_app.logger.error(f"Error deleting profile image: {e}")
            
            # 10. Delete the user account
            db.session.delete(current_user)
            db.session.commit()
            
            # Log successful deletion
            current_app.logger.info(f"User account deleted successfully: {username} (ID: {user_id})")
            
            # Send confirmation email (optional, if email service configured)
            try:
                from .email_service import send_email
                send_email(
                    to_email=user_email,
                    subject='Account Deleted - KickthisUSs',
                    body=f"Your account ({username}) has been permanently deleted as per your request.\n\nIf this was not you, please contact support immediately."
                )
            except Exception as e:
                current_app.logger.error(f"Failed to send deletion confirmation email: {e}")
            
            # Logout user
            from flask_login import logout_user
            logout_user()
            
            flash('Il tuo account è stato eliminato definitivamente. Grazie per aver utilizzato KickthisUSs.', 'success')
            return redirect(url_for('projects.home'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting user account {user_id}: {str(e)}")
            flash('Si è verificato un errore durante la cancellazione dell\'account. Riprova o contatta il supporto.', 'error')
            return render_template('users/delete_account.html')
    
    return render_template('users/delete_account.html')

# app/routes_investments.py

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from .models import (Project, ProjectVote, InvestmentProject, Investment, 
                    EquityConfiguration, User, Collaborator)
from .extensions import db
from datetime import datetime, timezone
from sqlalchemy import func, desc, and_
import calendar

investments_bp = Blueprint('investments', __name__, template_folder='templates')


@investments_bp.route('/investments')
def investments_page():
    """Pagina principale degli investimenti con i TOP 10 progetti più votati"""
    from sqlalchemy import func, desc
    
    # Query per ottenere i progetti con più voti totali (tutti i mesi)
    top_projects_query = db.session.query(
        Project.id,
        Project.name,
        Project.description,
        Project.creator_id,
        Project.created_at,
        func.count(ProjectVote.id).label('total_votes')
    ).outerjoin(ProjectVote, Project.id == ProjectVote.project_id)\
     .filter(Project.private == False)\
     .group_by(Project.id)\
     .order_by(desc(func.count(ProjectVote.id)), desc(Project.created_at))\
     .limit(10).all()
    
    # Converti i risultati in una lista più utilizzabile
    top_projects = []
    for result in top_projects_query:
        project = db.session.get(Project, result.id)
        if project:
            # Controlla se esiste già un InvestmentProject per questo progetto
            existing_investment = InvestmentProject.query.filter_by(project_id=project.id).first()
            
            # Se non esiste, crealo automaticamente
            if not existing_investment and result.total_votes > 0:
                # Ottieni configurazione equity o usa default
                equity_config = EquityConfiguration.query.filter_by(project_id=project.id).first()
                available_equity = equity_config.investors_percentage if equity_config else 10.0
                
                new_investment_project = InvestmentProject(
                    project_id=project.id,
                    publication_month=datetime.now().month,
                    publication_year=datetime.now().year,
                    total_votes=result.total_votes,
                    available_equity_percentage=available_equity,
                    equity_price_per_percent=100.0,  # Default price
                    is_active=True
                )
                db.session.add(new_investment_project)
                db.session.commit()
                existing_investment = new_investment_project
            
            if existing_investment:
                # Calcola statistiche investimento
                total_invested = db.session.query(func.sum(Investment.amount_paid)).filter(
                    Investment.investment_project_id == existing_investment.id
                ).scalar() or 0.0
                
                equity_sold = db.session.query(func.sum(Investment.equity_percentage)).filter(
                    Investment.investment_project_id == existing_investment.id
                ).scalar() or 0.0
                
                equity_remaining = max(0, existing_investment.available_equity_percentage - equity_sold)
                
                investors_count = Investment.query.filter(
                    Investment.investment_project_id == existing_investment.id
                ).count()
                
                top_projects.append({
                    'project': project,
                    'total_votes': result.total_votes,
                    'investment_project': existing_investment,
                    'total_invested': total_invested,
                    'equity_sold': equity_sold,
                    'equity_remaining': equity_remaining,
                    'investors_count': investors_count
                })
    
    return render_template('investments/investments_page.html', 
                         top_projects=top_projects)


@investments_bp.route('/vote_project/<int:project_id>', methods=['POST'])
@login_required
def vote_project(project_id):
    """Permette a un utente di votare un progetto (1 voto per utente per progetto)"""
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    
    # Verifica che il progetto esista e sia pubblico
    project = Project.query.get_or_404(project_id)
    if project.private:
        return jsonify({'success': False, 'message': 'Il progetto non è pubblico'})
    
    # Verifica se l'utente ha già votato questo progetto (mai, non solo questo mese)
    existing_vote = ProjectVote.query.filter(
        ProjectVote.project_id == project_id,
        ProjectVote.user_id == current_user.id
    ).first()
    
    if existing_vote:
        return jsonify({'success': False, 'message': 'Hai già votato questo progetto'})
    
    # Crea il nuovo voto
    new_vote = ProjectVote(
        project_id=project_id,
        user_id=current_user.id,
        vote_month=current_month,
        vote_year=current_year
    )
    
    db.session.add(new_vote)
    db.session.commit()
    
    # Conta i voti totali per il progetto (tutti i voti)
    total_votes = ProjectVote.query.filter(
        ProjectVote.project_id == project_id
    ).count()
    
    return jsonify({'success': True, 'message': 'Voto registrato!', 'total_votes': total_votes})


@investments_bp.route('/invest/<int:investment_project_id>')
@login_required
def invest_page(investment_project_id):
    """Pagina per investire in un progetto specifico"""
    investment_project = InvestmentProject.query.get_or_404(investment_project_id)
    
    # Calcola l'equity già venduta
    equity_sold = db.session.query(func.sum(Investment.equity_percentage)).filter(
        Investment.investment_project_id == investment_project_id
    ).scalar() or 0.0
    
    equity_remaining = max(0, investment_project.available_equity_percentage - equity_sold)
    
    # Recupera gli investimenti esistenti
    existing_investments = Investment.query.filter(
        Investment.investment_project_id == investment_project_id
    ).order_by(desc(Investment.created_at)).all()
    
    # Verifica se l'utente corrente è il creatore o un collaboratore del progetto
    is_creator = investment_project.project.creator_id == current_user.id
    is_collaborator = Collaborator.query.filter(
        Collaborator.project_id == investment_project.project_id,
        Collaborator.user_id == current_user.id
    ).first() is not None
    
    # Carica esplicitamente i tasks del progetto per evitare problemi con lazy loading
    project_tasks = list(investment_project.project.tasks)
    
    return render_template('investments/invest_page.html',
                         investment_project=investment_project,
                         project_tasks=project_tasks,
                         equity_remaining=equity_remaining,
                         equity_sold=equity_sold,
                         existing_investments=existing_investments,
                         is_creator=is_creator,
                         is_collaborator=is_collaborator,
                         can_configure_equity=(is_creator or is_collaborator))


@investments_bp.route('/make_investment/<int:investment_project_id>', methods=['POST'])
@login_required
def make_investment(investment_project_id):
    """Permette di effettuare un investimento"""
    investment_project = InvestmentProject.query.get_or_404(investment_project_id)
    
    try:
        equity_percentage = float(request.form.get('equity_percentage', 0))
        investment_type = request.form.get('investment_type', 'paid')  # 'paid' o 'free'
        
        if equity_percentage <= 0:
            flash('La percentuale di equity deve essere maggiore di 0', 'error')
            return redirect(url_for('investments.invest_page', investment_project_id=investment_project_id))
        
        # Verifica equity disponibile
        equity_sold = db.session.query(func.sum(Investment.equity_percentage)).filter(
            Investment.investment_project_id == investment_project_id
        ).scalar() or 0.0
        
        equity_remaining = max(0, investment_project.available_equity_percentage - equity_sold)
        
        if equity_percentage > equity_remaining:
            flash(f'Equity non sufficiente. Disponibile: {equity_remaining:.2f}%', 'error')
            return redirect(url_for('investments.invest_page', investment_project_id=investment_project_id))
        
        # Calcola l'importo
        amount_paid = 0.0
        if investment_type == 'paid':
            amount_paid = equity_percentage * investment_project.equity_price_per_percent
        
        # Crea l'investimento
        new_investment = Investment(
            investment_project_id=investment_project_id,
            investor_id=current_user.id,
            equity_percentage=equity_percentage,
            amount_paid=amount_paid,
            is_free_contribution=(investment_type == 'free'),
            investment_type=investment_type
        )
        
        db.session.add(new_investment)
        db.session.flush()  # Flush per ottenere l'ID
        
        # 🎯 DISTRIBUTE SHARES OR EQUITY (based on project system)
        project = investment_project.project
        try:
            if project.uses_shares_system():
                from app.services.share_service import ShareService
                share_service = ShareService()
                granted_shares = share_service.distribute_investment_shares(project, current_user.id, equity_percentage)
                
                if granted_shares:
                    shares_count = float(granted_shares.shares_count)
                    percentage = granted_shares.get_percentage()
                    current_app.logger.info(
                        f'✅ Granted {shares_count} shares ({percentage:.2f}%) to investor {current_user.id} for investment in project {project.id}'
                    )
            # Note: Old equity system is handled by Collaborator.equity_share (already exists in code)
        except Exception as distribution_error:
            current_app.logger.warning(
                f'⚠️ Could not distribute shares for investment: {str(distribution_error)}'
            )
            # Non bloccare l'investimento se la distribuzione shares fallisce
        
        db.session.commit()
        
        if investment_type == 'free':
            if project.uses_shares_system():
                shares_count = float(project.get_user_shares_count(current_user.id))
                percentage = project.get_user_shares_percentage(current_user.id)
                flash(f'Grazie per il tuo contributo gratuito! Hai ricevuto {shares_count:.0f} shares ({percentage:.2f}% partecipazione)', 'success')
            else:
                flash(f'Grazie per il tuo contributo gratuito di {equity_percentage:.2f}%!', 'success')
        else:
            if project.uses_shares_system():
                shares_count = float(project.get_user_shares_count(current_user.id))
                percentage = project.get_user_shares_percentage(current_user.id)
                flash(f'Investimento completato! Hai ricevuto {shares_count:.0f} shares ({percentage:.2f}% partecipazione) per €{amount_paid:.2f}', 'success')
            else:
                flash(f'Investimento completato! {equity_percentage:.2f}% per €{amount_paid:.2f}', 'success')
            
    except ValueError:
        flash('Dati di investimento non validi', 'error')
    
    return redirect(url_for('investments.invest_page', investment_project_id=investment_project_id))


@investments_bp.route('/configure_equity/<int:project_id>')
@login_required
def configure_equity_page(project_id):
    """Pagina per configurare l'equity del progetto (solo per creatore e collaboratori)"""
    project = Project.query.get_or_404(project_id)
    
    # Verifica che l'utente sia il creatore O un collaboratore del progetto
    is_creator = project.creator_id == current_user.id
    is_collaborator = Collaborator.query.filter(
        Collaborator.project_id == project_id,
        Collaborator.user_id == current_user.id
    ).first() is not None
    
    if not (is_creator or is_collaborator):
        flash('Non hai i permessi per configurare l\'equity di questo progetto. Solo il creatore e i collaboratori possono farlo.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    # Recupera la configurazione corrente o crea una nuova
    equity_config = EquityConfiguration.query.filter_by(project_id=project_id).first()
    if not equity_config:
        equity_config = EquityConfiguration(
            project_id=project_id,
            last_updated_by=current_user.id
        )
        db.session.add(equity_config)
        db.session.commit()
    
    # Recupera o crea InvestmentProject per gestire il prezzo
    investment_project = InvestmentProject.query.filter_by(project_id=project_id).first()
    if not investment_project:
        investment_project = InvestmentProject(
            project_id=project_id,
            publication_month=datetime.now().month,
            publication_year=datetime.now().year,
            total_votes=0,
            available_equity_percentage=equity_config.investors_percentage,
            equity_price_per_percent=100.0,  # Default price
            is_active=True
        )
        db.session.add(investment_project)
        db.session.commit()
    
    return render_template('investments/configure_equity.html',
                         project=project,
                         equity_config=equity_config,
                         investment_project=investment_project,
                         is_creator=is_creator,
                         is_collaborator=is_collaborator)


@investments_bp.route('/update_equity_config/<int:project_id>', methods=['POST'])
@login_required
def update_equity_config(project_id):
    """Aggiorna la configurazione dell'equity (solo creatore e collaboratori)"""
    project = Project.query.get_or_404(project_id)
    
    # Verifica che l'utente sia il creatore O un collaboratore del progetto
    is_creator = project.creator_id == current_user.id
    is_collaborator = Collaborator.query.filter(
        Collaborator.project_id == project_id,
        Collaborator.user_id == current_user.id
    ).first() is not None
    
    if not (is_creator or is_collaborator):
        flash('Non hai i permessi per configurare l\'equity di questo progetto. Solo il creatore e i collaboratori possono farlo.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    try:
        investors_percentage = float(request.form.get('investors_percentage', 10.0))
        equity_price = float(request.form.get('equity_price', 100.0))  # Nuovo campo per il prezzo
        
        # Validazione percentuale: deve essere tra 0 e 99 (1% sempre per KickthisUSs)
        if investors_percentage < 0 or investors_percentage > 99:
            flash('La percentuale per gli investitori deve essere tra 0% e 99%', 'error')
            return redirect(url_for('investments.configure_equity_page', project_id=project_id))
            
        # Validazione prezzo: deve essere positivo
        if equity_price <= 0:
            flash('Il prezzo per ogni 1% di equity deve essere maggiore di 0 EUR', 'error')
            return redirect(url_for('investments.configure_equity_page', project_id=project_id))
        
        team_percentage = 99.0 - investors_percentage  # Il resto al team (escludendo l'1% di KickthisUSs)
        
        # Aggiorna la configurazione percentuali
        equity_config = EquityConfiguration.query.filter_by(project_id=project_id).first()
        if equity_config:
            equity_config.investors_percentage = investors_percentage
            equity_config.team_percentage = team_percentage
            equity_config.last_updated_by = current_user.id
            equity_config.updated_at = datetime.now(timezone.utc)
        else:
            equity_config = EquityConfiguration(
                project_id=project_id,
                investors_percentage=investors_percentage,
                team_percentage=team_percentage,
                last_updated_by=current_user.id
            )
            db.session.add(equity_config)
        
        # Aggiorna/crea InvestmentProject con il nuovo prezzo
        investment_project = InvestmentProject.query.filter_by(project_id=project_id).first()
        if investment_project:
            investment_project.equity_price_per_percent = equity_price
            investment_project.available_equity_percentage = investors_percentage
        else:
            investment_project = InvestmentProject(
                project_id=project_id,
                publication_month=datetime.now().month,
                publication_year=datetime.now().year,
                total_votes=0,
                available_equity_percentage=investors_percentage,
                equity_price_per_percent=equity_price,
                is_active=True
            )
            db.session.add(investment_project)
        
        db.session.commit()
        flash('Configurazione equity e prezzo aggiornati con successo!', 'success')
        
    except ValueError:
        flash('Dati non validi', 'error')
    
    return redirect(url_for('investments.configure_equity_page', project_id=project_id))


# Route /voting rimossa - ora i voti si fanno direttamente dalle pagine dei progetti
# Il sistema TOP 10 è automatico e sempre attivo
    
    return render_template('investments/voting_page.html',
                         projects_with_votes=projects_with_votes,
                         current_month_name=calendar.month_name[current_date.month],
                         current_year=current_year)



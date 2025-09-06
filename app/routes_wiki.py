# app/routes_wiki.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from .models import WikiPage, WikiRevision, Project, Collaborator
from .decorators import role_required
from .extensions import db
import re

wiki_bp = Blueprint('wiki', __name__)

def slugify(text):
    """Converte il testo in un slug URL-friendly"""
    # Rimuove caratteri speciali e converte in lowercase
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().lower()
    # Sostituisce spazi con trattini
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug

def check_wiki_access(project_id):
    """Verifica se l'utente può accedere alla Wiki del progetto"""
    project = Project.query.get_or_404(project_id)
    
    # Il creatore del progetto ha sempre accesso
    if project.creator_id == current_user.id:
        return True
    
    # Verifica se l'utente è un collaboratore del progetto
    collaborator = Collaborator.query.filter_by(
        project_id=project_id,
        user_id=current_user.id
    ).first()
    
    return collaborator is not None

@wiki_bp.route('/projects/<int:project_id>/wiki')
@login_required
def wiki_index(project_id):
    """Pagina principale della Wiki del progetto"""
    if not check_wiki_access(project_id):
        flash('Non hai i permessi per accedere alla Wiki di questo progetto.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    wiki_pages = WikiPage.query.filter_by(project_id=project_id).order_by(WikiPage.title).all()
    
    # Se non ci sono pagine, creiamo una pagina di benvenuto
    if not wiki_pages:
        return render_template('wiki/empty_wiki.html', project=project)
    
    return render_template('wiki/index.html', project=project, wiki_pages=wiki_pages)

@wiki_bp.route('/projects/<int:project_id>/wiki/new', methods=['GET', 'POST'])
@login_required
def create_wiki_page(project_id):
    """Crea una nuova pagina Wiki"""
    if not check_wiki_access(project_id):
        flash('Non hai i permessi per accedere alla Wiki di questo progetto.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not title or not content:
            flash('Titolo e contenuto sono obbligatori.', 'error')
            return render_template('wiki/create.html', project=project)
        
        # Genera slug unico
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        while WikiPage.query.filter_by(project_id=project_id, slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Crea la pagina Wiki
        wiki_page = WikiPage(
            project_id=project_id,
            title=title,
            slug=slug,
            content=content,
            created_by=current_user.id
        )
        
        db.session.add(wiki_page)
        db.session.commit()
        
        # Crea la prima revisione
        revision = WikiRevision(
            page_id=wiki_page.id,
            content=content,
            edited_by=current_user.id,
            edit_summary="Creazione pagina"
        )
        
        db.session.add(revision)
        db.session.commit()
        
        flash('Pagina Wiki creata con successo!', 'success')
        return redirect(url_for('wiki.view_wiki_page', project_id=project_id, slug=slug))
    
    return render_template('wiki/create.html', project=project)

@wiki_bp.route('/projects/<int:project_id>/wiki/<slug>')
@login_required
def view_wiki_page(project_id, slug):
    """Visualizza una pagina Wiki"""
    if not check_wiki_access(project_id):
        flash('Non hai i permessi per accedere alla Wiki di questo progetto.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    wiki_page = WikiPage.query.filter_by(project_id=project_id, slug=slug).first_or_404()
    
    # Verifica se l'utente è collaboratore per i pulsanti AI
    is_collaborator = False
    if current_user.is_authenticated:
        from app.models import Collaborator
        is_collaborator = Collaborator.query.filter_by(
            project_id=project_id,
            user_id=current_user.id
        ).first() is not None
    
    return render_template('wiki/view.html', 
                          project=project, 
                          wiki_page=wiki_page,
                          is_collaborator=is_collaborator)

@wiki_bp.route('/projects/<int:project_id>/wiki/<slug>/edit', methods=['GET', 'POST'])
@login_required
def edit_wiki_page(project_id, slug):
    """Modifica una pagina Wiki"""
    if not check_wiki_access(project_id):
        flash('Non hai i permessi per accedere alla Wiki di questo progetto.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    wiki_page = WikiPage.query.filter_by(project_id=project_id, slug=slug).first_or_404()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        edit_summary = request.form.get('edit_summary', '').strip()
        
        if not title or not content:
            flash('Titolo e contenuto sono obbligatori.', 'error')
            return render_template('wiki/edit.html', project=project, wiki_page=wiki_page)
        
        # Aggiorna la pagina solo se ci sono modifiche
        if wiki_page.title != title or wiki_page.content != content:
            # Genera nuovo slug se il titolo è cambiato
            if wiki_page.title != title:
                base_slug = slugify(title)
                new_slug = base_slug
                counter = 1
                while (WikiPage.query.filter_by(project_id=project_id, slug=new_slug)
                       .filter(WikiPage.id != wiki_page.id).first()):
                    new_slug = f"{base_slug}-{counter}"
                    counter += 1
                wiki_page.slug = new_slug
            
            wiki_page.title = title
            wiki_page.content = content
            
            # Crea revisione
            revision = WikiRevision(
                page_id=wiki_page.id,
                content=content,
                edited_by=current_user.id,
                edit_summary=edit_summary or "Modifica pagina"
            )
            
            db.session.add(revision)
            db.session.commit()
            
            flash('Pagina Wiki aggiornata con successo!', 'success')
            return redirect(url_for('wiki.view_wiki_page', project_id=project_id, slug=wiki_page.slug))
        else:
            flash('Nessuna modifica rilevata.', 'info')
    
    return render_template('wiki/edit.html', project=project, wiki_page=wiki_page)

@wiki_bp.route('/projects/<int:project_id>/wiki/<slug>/history')
@login_required
def wiki_history(project_id, slug):
    """Visualizza la cronologia delle modifiche di una pagina Wiki"""
    if not check_wiki_access(project_id):
        flash('Non hai i permessi per accedere alla Wiki di questo progetto.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    wiki_page = WikiPage.query.filter_by(project_id=project_id, slug=slug).first_or_404()
    revisions = WikiRevision.query.filter_by(page_id=wiki_page.id).order_by(WikiRevision.created_at.desc()).all()
    
    return render_template('wiki/history.html', project=project, wiki_page=wiki_page, revisions=revisions)

@wiki_bp.route('/projects/<int:project_id>/wiki/<slug>/revision/<int:revision_id>')
@login_required
def view_wiki_revision(project_id, slug, revision_id):
    """Visualizza una revisione specifica di una pagina Wiki"""
    if not check_wiki_access(project_id):
        flash('Non hai i permessi per accedere alla Wiki di questo progetto.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    wiki_page = WikiPage.query.filter_by(project_id=project_id, slug=slug).first_or_404()
    revision = WikiRevision.query.filter_by(page_id=wiki_page.id, id=revision_id).first_or_404()
    
    return render_template('wiki/revision.html', project=project, wiki_page=wiki_page, revision=revision)

@wiki_bp.route('/projects/<int:project_id>/wiki/<slug>/delete', methods=['POST'])
@login_required
def delete_wiki_page(project_id, slug):
    """Elimina una pagina Wiki"""
    if not check_wiki_access(project_id):
        flash('Non hai i permessi per accedere alla Wiki di questo progetto.', 'error')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    project = Project.query.get_or_404(project_id)
    wiki_page = WikiPage.query.filter_by(project_id=project_id, slug=slug).first_or_404()
    
    # Solo il creatore della pagina o il proprietario del progetto possono eliminarla
    if wiki_page.created_by != current_user.id and project.creator_id != current_user.id:
        flash('Non hai i permessi per eliminare questa pagina.', 'error')
        return redirect(url_for('wiki.view_wiki_page', project_id=project_id, slug=slug))
    
    db.session.delete(wiki_page)
    db.session.commit()
    
    flash('Pagina Wiki eliminata con successo.', 'success')
    return redirect(url_for('wiki.wiki_index', project_id=project_id))

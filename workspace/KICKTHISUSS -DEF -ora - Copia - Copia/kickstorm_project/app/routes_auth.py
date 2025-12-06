# app/routes_auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime, timezone, timedelta
import qrcode
import io
import base64

from .forms import RegistrationForm, LoginForm, ForgotPasswordForm, ResetPasswordForm, TwoFactorSetupForm, TwoFactorForm, DisableTwoFactorForm
from .models import User
from app.extensions import limiter

# --- MODIFICA CHIAVE ---
# Importiamo 'db' dal file centralizzato 'extensions.py'.
from .extensions import db

# Crea un Blueprint per le route di autenticazione
auth_bp = Blueprint('auth', __name__, template_folder='templates/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute;20 per hour")  # Limita tentativi di registrazione
def register():
    # Se l'utente è già loggato, reindirizzalo alla homepage
    if current_user.is_authenticated:
        return redirect(url_for('projects.home'))
    
    form = RegistrationForm()
    # validate_on_submit() controlla se il form è stato inviato (POST) e se è valido
    if form.validate_on_submit():
        # Crea un nuovo utente con i dati validati del form
        new_user = User(
            username=form.username.data,
            email=form.email.data
        )
        new_user.set_password(form.password.data) # Imposta la password hashata
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Invia email di verifica
            from .email_service import send_verification_email
            if send_verification_email(new_user):
                db.session.commit()  # Salva il token
                flash(f'Account creato con successo per {form.username.data}! Ti abbiamo inviato un\'email per verificare il tuo account.', 'success')
            else:
                flash(f'Account creato per {form.username.data}, ma errore nell\'invio dell\'email di verifica. Contattaci per supporto.', 'warning')
            
            current_app.logger.info(f"Nuovo utente registrato: {form.username.data}, Email: {form.email.data}")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore durante la registrazione dell'utente {form.username.data}: {e}", exc_info=True)
            flash('Si è verificato un errore durante la creazione del tuo account. Riprova.', 'danger')
            
    # Se la richiesta è GET o il form non è valido, mostra di nuovo la pagina di registrazione
    return render_template('register.html', title='Registrati', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute;20 per hour")  # Limita tentativi di login
def login():
    if current_user.is_authenticated:
        return redirect(url_for('projects.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email_for_login = form.email.data
        password_for_login = form.password.data
        
        user = User.query.filter_by(email=email_for_login).first()
        
        if user and user.check_password(password_for_login):
            # Se l'utente ha 2FA abilitato, reindirizza alla verifica 2FA
            if user.two_factor_enabled:
                session['user_id_2fa'] = user.id
                session['remember_me'] = form.remember.data
                return redirect(url_for('auth.two_factor'))
            else:
                # Login normale senza 2FA
                login_user(user, remember=form.remember.data)
                flash('Login effettuato con successo!', 'success')
                
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('projects.home'))
        else:
            flash('Login non riuscito. Controlla email e password.', 'danger')
            
    return render_template('login.html', title='Login', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    user_username = current_user.username
    logout_user()
    flash('Logout effettuato con successo.', 'info')
    current_app.logger.info(f"Utente {user_username} ha effettuato il logout.")
    return redirect(url_for('projects.home'))

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verifica l'email dell'utente tramite token."""
    user = User.query.filter_by(email_verification_token=token).first()
    
    if not user:
        flash('Token di verifica non valido o scaduto.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Verifica se il token non è scaduto (24 ore)
    if user.email_verification_sent_at:
        sent_at = user.email_verification_sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - sent_at > timedelta(hours=24):
            flash('Token di verifica scaduto. Richiedi una nuova verifica.', 'warning')
            return redirect(url_for('auth.login'))
    
    # Verifica l'email
    user.verify_email()
    db.session.commit()
    
    # Invia email di benvenuto
    from .email_service import send_welcome_email
    send_welcome_email(user)
    
    flash('Email verificata con successo! Benvenuto su KICKStorm! 🎉', 'success')
    current_app.logger.info(f"Email verificata per utente: {user.username}")
    
    # Effettua automaticamente il login
    login_user(user)
    return redirect(url_for('projects.home'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Richiesta reset password."""
    if current_user.is_authenticated:
        return redirect(url_for('projects.home'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            # Invia email di reset solo se l'account è verificato
            if not user.email_verified:
                flash('Devi prima verificare il tuo account. Controlla la tua email per il link di verifica.', 'warning')
                return redirect(url_for('auth.login'))
            
            from .email_service import send_password_reset_email
            if send_password_reset_email(user):
                db.session.commit()
                flash('Email con le istruzioni per il reset della password inviata! Controlla la tua casella di posta.', 'info')
            else:
                flash('Errore nell\'invio dell\'email. Riprova più tardi.', 'danger')
        else:
            # Per sicurezza, mostra sempre lo stesso messaggio
            flash('Email con le istruzioni per il reset della password inviata! Controlla la tua casella di posta.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password tramite token."""
    if current_user.is_authenticated:
        return redirect(url_for('projects.home'))
    
    user = User.query.filter_by(password_reset_token=token).first()
    
    if not user:
        flash('Token di reset non valido o scaduto.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    # Verifica se il token non è scaduto (1 ora)
    if user.password_reset_sent_at:
        sent_at = user.password_reset_sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - sent_at > timedelta(hours=1):
            flash('Token di reset scaduto. Richiedi un nuovo reset.', 'warning')
            return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.reset_password(form.password.data)
        db.session.commit()
        
        flash('Password reimpostata con successo! Ora puoi effettuare il login.', 'success')
        current_app.logger.info(f"Password reimpostata per utente: {user.username}")
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)

@auth_bp.route('/resend-verification')
@login_required
def resend_verification():
    """Invia nuovamente l'email di verifica."""
    if current_user.email_verified:
        flash('Il tuo account è già verificato!', 'info')
        return redirect(url_for('projects.home'))
    
    from .email_service import send_verification_email
    if send_verification_email(current_user):
        db.session.commit()
        flash('Email di verifica inviata nuovamente! Controlla la tua casella di posta.', 'info')
    else:
        flash('Errore nell\'invio dell\'email. Riprova più tardi.', 'danger')
    
    return redirect(url_for('projects.home'))

# --- 2FA Routes ---
@auth_bp.route('/two-factor', methods=['GET', 'POST'])
def two_factor():
    """Verifica 2FA durante il login"""
    if 'user_id_2fa' not in session:
        flash('Sessione scaduta. Effettua nuovamente il login.', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id_2fa'])
    if not user or not user.two_factor_enabled:
        session.pop('user_id_2fa', None)
        flash('Errore di autenticazione.', 'danger')
        return redirect(url_for('auth.login'))
    
    form = TwoFactorForm()
    if form.validate_on_submit():
        token = form.token.data
        
        # Verifica TOTP o codice di backup
        if user.verify_totp(token) or user.use_backup_code(token):
            # Completa il login
            remember_me = session.pop('remember_me', False)
            session.pop('user_id_2fa', None)
            
            if user.use_backup_code(token):
                db.session.commit()  # Salva la rimozione del codice di backup
                flash('Login completato con codice di backup. Considera di rigenerare i codici di backup.', 'warning')
            
            login_user(user, remember=remember_me)
            flash('Login 2FA completato con successo!', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('projects.home'))
        else:
            flash('Codice non valido. Riprova.', 'danger')
    
    return render_template('auth/two_factor.html', form=form)

@auth_bp.route('/setup-2fa', methods=['GET', 'POST'])
@login_required
def setup_two_factor():
    """Setup iniziale del 2FA"""
    if current_user.two_factor_enabled:
        flash('2FA è già abilitato per il tuo account.', 'info')
        return redirect(url_for('users.profile'))
    
    form = TwoFactorSetupForm()
    
    # Genera un nuovo secret se non esiste
    if not current_user.totp_secret:
        current_user.generate_totp_secret()
        db.session.commit()
    
    # Genera QR code
    qr_uri = current_user.get_totp_uri()
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    if form.validate_on_submit():
        if current_user.verify_totp(form.token.data):
            # Genera codici di backup
            backup_codes = current_user.generate_backup_codes()
            current_user.enable_two_factor()
            db.session.commit()
            
            flash('2FA abilitato con successo!', 'success')
            return render_template('auth/backup_codes.html', backup_codes=backup_codes)
        else:
            flash('Codice non valido. Riprova.', 'danger')
    
    return render_template('auth/setup_2fa.html', form=form, qr_code=img_str, secret=current_user.totp_secret)

@auth_bp.route('/disable-2fa', methods=['GET', 'POST'])
@login_required
def disable_two_factor():
    """Disabilita 2FA"""
    if not current_user.two_factor_enabled:
        flash('2FA non è abilitato per il tuo account.', 'info')
        return redirect(url_for('users.profile'))
    
    form = DisableTwoFactorForm()
    if form.validate_on_submit():
        if current_user.check_password(form.password.data):
            if current_user.verify_totp(form.token.data) or current_user.use_backup_code(form.token.data):
                current_user.disable_two_factor()
                db.session.commit()
                flash('2FA disabilitato con successo.', 'success')
                return redirect(url_for('users.profile'))
            else:
                flash('Codice 2FA non valido.', 'danger')
        else:
            flash('Password non corretta.', 'danger')
    
    return render_template('auth/disable_2fa.html', form=form)
# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, FloatField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, NumberRange
from .models import User, ALLOWED_TASK_PHASES, ALLOWED_TASK_DIFFICULTIES, ALLOWED_TASK_TYPES

# Form di base che fornisce solo la protezione CSRF.
# Utile per i form semplici che contengono solo un pulsante di invio.
class BaseForm(FlaskForm):
    pass

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(message="L'username è obbligatorio."),
                                       Length(min=3, max=20, message="L'username deve essere tra 3 e 20 caratteri.")])
    email = StringField('Email',
                        validators=[DataRequired(message="L'email è obbligatoria."),
                                    Email(message="Inserisci un indirizzo email valido.")])
    password = PasswordField('Password',
                             validators=[DataRequired(message="La password è obbligatoria."),
                                         Length(min=6, message="La password deve essere di almeno 6 caratteri.")])
    confirm_password = PasswordField('Conferma Password',
                                     validators=[DataRequired(message="Conferma la password."),
                                                 EqualTo('password', message="Le password non coincidono.")])
    submit = SubmitField('Registrati')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Questo username è già stato preso. Scegline un altro.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Questa email è già in uso. Scegline una diversa o effettua il login.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(message="L'email è obbligatoria."),
                                    Email(message="Inserisci un indirizzo email valido.")])
    password = PasswordField('Password', validators=[DataRequired(message="La password è obbligatoria.")])
    remember = BooleanField('Ricordami') # Opzione "Ricordami"
    submit = SubmitField('Login')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(message="L'email è obbligatoria."),
                                    Email(message="Inserisci un indirizzo email valido.")])
    submit = SubmitField('Invia Link Reset')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nuova Password',
                             validators=[DataRequired(message="La password è obbligatoria."),
                                         Length(min=6, message="La password deve essere di almeno 6 caratteri.")])
    confirm_password = PasswordField('Conferma Nuova Password',
                                     validators=[DataRequired(message="Conferma la password."),
                                                 EqualTo('password', message="Le password non coincidono.")])
    submit = SubmitField('Imposta Nuova Password')

class SolutionForm(FlaskForm):
    solution_content = TextAreaField('Descrizione della Soluzione',
                                     validators=[DataRequired("La soluzione non può essere vuota.")],
                                     render_kw={"rows": 8, "class": "form-input block w-full rounded-lg border-gray-300 shadow-sm focus:border-mclaren-orange focus:ring focus:ring-mclaren-orange focus:ring-opacity-50", "placeholder": "Descrivi in dettaglio la tua implementazione, il tuo approccio e i risultati..."})
    solution_file = FileField('Allega un File (Opzionale)',
                              validators=[Optional(), FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'txt', 'pdf', 'zip', 'rar'], 'Tipo di file non supportato!')])
    submit = SubmitField('Invia Soluzione')

class AddTaskForm(FlaskForm):
    title = StringField('Titolo del Task', validators=[DataRequired(), Length(min=5, max=150)])
    description = TextAreaField('Descrizione', validators=[DataRequired(), Length(min=20)], render_kw={"rows": 5})
    task_type = SelectField('Tipo di Task', choices=list(ALLOWED_TASK_TYPES.items()), validators=[DataRequired()])
    phase = SelectField('Fase del Progetto', choices=list(ALLOWED_TASK_PHASES.items()), validators=[DataRequired()])
    difficulty = SelectField('Difficoltà', choices=list(ALLOWED_TASK_DIFFICULTIES.items()), validators=[DataRequired()])
    equity_reward = FloatField('Ricompensa in Equity (%)', validators=[DataRequired(), NumberRange(min=0.01, max=10, message="L'equity deve essere tra 0.01% e 10%.")])
    is_private = BooleanField('Task Privato', description='Solo il creatore del progetto e i collaboratori potranno vedere questo task')
    
    # Campi specifici per esperimenti di validazione
    hypothesis = TextAreaField('Ipotesi da Testare', validators=[Optional()], render_kw={"rows": 3, "placeholder": "Es: Crediamo che i nostri utenti siano disposti a pagare 5€/mese per la funzionalità X"})
    test_method = TextAreaField('Metodo di Test', validators=[Optional()], render_kw={"rows": 3, "placeholder": "Es: Creare una landing page e lanciare una campagna pubblicitaria da 50€"})
    results = TextAreaField('Risultati', validators=[Optional()], render_kw={"rows": 3, "placeholder": "Es: Ipotesi invalidata, il tasso di conversione è stato troppo basso"})
    
    submit = SubmitField('Aggiungi Task')
    
    def validate_hypothesis(self, field):
        if self.task_type.data == 'validation' and not field.data:
            raise ValidationError('L\'ipotesi è obbligatoria per gli esperimenti di validazione.')
    
    def validate_test_method(self, field):
        if self.task_type.data == 'validation' and not field.data:
            raise ValidationError('Il metodo di test è obbligatorio per gli esperimenti di validazione.')

class UpdateProfileForm(FlaskForm):
    profile_image = FileField('Immagine Profilo', 
                             validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 
                                                   'Solo immagini JPG, JPEG, PNG e GIF sono consentite')])
    submit = SubmitField('Aggiorna Profilo')

# --- 2FA Forms ---
class TwoFactorSetupForm(FlaskForm):
    """Form per abilitare 2FA"""
    token = StringField('Codice Autenticazione', 
                       validators=[DataRequired(message="Il codice è obbligatorio."),
                                   Length(min=6, max=6, message="Il codice deve essere di 6 cifre.")])
    submit = SubmitField('Abilita 2FA')

class TwoFactorForm(FlaskForm):
    """Form per inserire il codice 2FA durante il login"""
    token = StringField('Codice Autenticazione', 
                       validators=[DataRequired(message="Il codice è obbligatorio."),
                                   Length(min=6, max=8, message="Il codice deve essere di 6 cifre o un codice di backup.")])
    submit = SubmitField('Verifica')

class DisableTwoFactorForm(FlaskForm):
    """Form per disabilitare 2FA"""
    password = PasswordField('Password', 
                            validators=[DataRequired(message="La password è obbligatoria.")])
    token = StringField('Codice Autenticazione', 
                       validators=[DataRequired(message="Il codice è obbligatorio."),
                                   Length(min=6, max=8, message="Il codice deve essere di 6 cifre o un codice di backup.")])
    submit = SubmitField('Disabilita 2FA')

# tests/factories/user_factory.py
import factory
from faker import Faker
from app.models import User
from app.extensions import db
from werkzeug.security import generate_password_hash

fake = Faker()

class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory per creare utenti di test."""
    
    class Meta:
        model = User
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = 'commit'

    id = factory.Sequence(lambda n: n + 1)
    username = factory.LazyFunction(lambda: fake.user_name())
    email = factory.LazyFunction(lambda: fake.email())
    password_hash = factory.LazyFunction(lambda: generate_password_hash('testpassword'))
    profile_image_url = factory.LazyFunction(lambda: fake.image_url())
    created_at = factory.LazyFunction(lambda: fake.date_time_this_year())
    
    @factory.post_generation
    def verify_email(obj, create, extracted, **kwargs):
        """Opzionalmente verifica l'email."""
        if extracted:
            obj.email_verified = True

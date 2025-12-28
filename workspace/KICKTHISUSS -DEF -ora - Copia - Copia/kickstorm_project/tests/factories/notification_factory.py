# tests/factories/notification_factory.py
import factory
from faker import Faker
from app.models import Notification
from app.extensions import db
from .user_factory import UserFactory
from .project_factory import ProjectFactory

fake = Faker()

class NotificationFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory per creare notifiche di test."""
    
    class Meta:
        model = Notification
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = 'commit'

    id = factory.Sequence(lambda n: n + 1)
    type = factory.LazyFunction(lambda: fake.random_element(['solution_published', 'solution_approved', 'task_created', 'project_update']))
    message = factory.LazyFunction(lambda: fake.sentence())
    is_read = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=40))
    timestamp = factory.LazyFunction(lambda: fake.date_time_this_year())
    
    # Relazioni
    user = factory.SubFactory(UserFactory)
    project = factory.SubFactory(ProjectFactory)

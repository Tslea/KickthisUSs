# tests/factories/project_factory.py
import factory
from faker import Faker
from app.models import Project, ALLOWED_PROJECT_CATEGORIES
from app.extensions import db
from .user_factory import UserFactory

fake = Faker()

class ProjectFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory per creare progetti di test."""
    
    class Meta:
        model = Project
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = 'commit'

    id = factory.Sequence(lambda n: n + 1)
    name = factory.LazyFunction(lambda: fake.catch_phrase())
    pitch = factory.LazyFunction(lambda: fake.text(max_nb_chars=400))
    description = factory.LazyFunction(lambda: fake.text(max_nb_chars=1000))
    category = factory.LazyFunction(lambda: fake.random_element(list(ALLOWED_PROJECT_CATEGORIES.keys())))
    cover_image_url = factory.LazyFunction(lambda: fake.image_url())
    repository_url = factory.LazyFunction(lambda: fake.url())
    created_at = factory.LazyFunction(lambda: fake.date_time_this_year())
    
    # Relazioni
    creator = factory.SubFactory(UserFactory)
    
    @factory.post_generation
    def with_tasks(obj, create, extracted, **kwargs):
        """Opzionalmente crea task per il progetto."""
        if extracted:
            from .task_factory import TaskFactory
            for _ in range(extracted):
                TaskFactory(project=obj, creator=obj.creator)

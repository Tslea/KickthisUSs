# tests/factories/task_factory.py
import factory
from faker import Faker
from app.models import Task, ALLOWED_TASK_TYPES, ALLOWED_TASK_PHASES, ALLOWED_TASK_STATUS, ALLOWED_TASK_DIFFICULTIES
from app.extensions import db
from .user_factory import UserFactory
from .project_factory import ProjectFactory

fake = Faker()

class TaskFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory per creare task di test."""
    
    class Meta:
        model = Task
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = 'commit'

    id = factory.Sequence(lambda n: n + 1)
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=4))
    description = factory.LazyFunction(lambda: fake.text(max_nb_chars=500))
    task_type = factory.LazyFunction(lambda: fake.random_element(list(ALLOWED_TASK_TYPES.keys())))
    phase = factory.LazyFunction(lambda: fake.random_element(list(ALLOWED_TASK_PHASES.keys())))
    status = factory.LazyFunction(lambda: fake.random_element(list(ALLOWED_TASK_STATUS.keys())))
    difficulty = factory.LazyFunction(lambda: fake.random_element(list(ALLOWED_TASK_DIFFICULTIES.keys())))
    equity_reward = factory.LazyFunction(lambda: fake.random_number(digits=2))
    is_private = False  # Default public task
    
    # Relazioni
    creator = factory.SubFactory(UserFactory)
    project = factory.SubFactory(ProjectFactory)
    
    @factory.post_generation
    def with_solutions(obj, create, extracted, **kwargs):
        """Opzionalmente crea soluzioni per il task."""
        if extracted:
            from .solution_factory import SolutionFactory
            for _ in range(extracted):
                SolutionFactory(task=obj)

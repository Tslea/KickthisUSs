# tests/factories/solution_factory.py
import factory
from faker import Faker
from app.models import Solution
from app.extensions import db
from .user_factory import UserFactory
from .task_factory import TaskFactory

fake = Faker()

class SolutionFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory per creare soluzioni di test."""
    
    class Meta:
        model = Solution
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = 'commit'

    id = factory.Sequence(lambda n: n + 1)
    solution_content = factory.LazyFunction(lambda: fake.text(max_nb_chars=1000))
    pull_request_url = factory.LazyFunction(lambda: fake.url())
    file_path = factory.LazyFunction(lambda: fake.file_path())
    is_approved = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=30))
    ai_coherence_score = factory.LazyFunction(lambda: fake.pyfloat(min_value=0, max_value=100))
    ai_completeness_score = factory.LazyFunction(lambda: fake.pyfloat(min_value=0, max_value=100))
    
    # Relazioni
    submitter = factory.SubFactory(UserFactory)
    task = factory.SubFactory(TaskFactory)
    
    @factory.post_generation  
    def set_user_id(obj, create, extracted, **kwargs):
        """Imposta submitted_by_user_id basato su submitter."""
        if create and hasattr(obj, 'submitter'):
            obj.submitted_by_user_id = obj.submitter.id
    
    @factory.post_generation
    def with_votes(obj, create, extracted, **kwargs):
        """Opzionalmente crea voti per la soluzione."""
        if extracted:
            from .vote_factory import VoteFactory
            for _ in range(extracted):
                VoteFactory(solution=obj)

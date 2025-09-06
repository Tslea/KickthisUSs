# tests/factories/vote_factory.py
import factory
from faker import Faker
from app.models import Vote
from app.extensions import db
from .user_factory import UserFactory
from .solution_factory import SolutionFactory

fake = Faker()

class VoteFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory per creare voti di test."""
    
    class Meta:
        model = Vote
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = 'commit'

    id = factory.Sequence(lambda n: n + 1)
    is_upvote = factory.LazyFunction(lambda: fake.boolean(chance_of_getting_true=70))
    created_at = factory.LazyFunction(lambda: fake.date_time_this_year())
    
    # Relazioni
    user = factory.SubFactory(UserFactory)
    solution = factory.SubFactory(SolutionFactory)

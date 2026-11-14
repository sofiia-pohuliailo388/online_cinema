
import pytest

from src.accounts.enums import UserGroupEnum
from src.accounts.models import User, UserGroup
from src.movies.models import Certification, Movie


@pytest.fixture
async def test_user(db_session):
    group = UserGroup(name=UserGroupEnum.USER)
    db_session.add(group)
    await db_session.flush()

    user = User(
        email="cart_user@test.com",
        hashed_password="test_hash",
        is_active=True,
        group_id=group.id,
    )
    db_session.add(user)
    await db_session.commit()

    return user


@pytest.fixture
async def movie(db_session):
    certification = Certification(name="PG-13")
    db_session.add(certification)
    await db_session.flush()

    movie = Movie(
        name="Inception",
        year=2010,
        time=148,
        imdb=8.8,
        votes=100000,
        description="A science fiction movie",
        price="9.99",
        certification_id=certification.id,
    )
    db_session.add(movie)
    await db_session.commit()

    return movie

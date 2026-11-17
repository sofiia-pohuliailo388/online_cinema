import pytest

from tests.payments.helpers import create_movie, create_order, create_user


@pytest.fixture
async def user(db_session):
    return await create_user(db_session, "payer@example.com")


@pytest.fixture
async def movie(db_session):
    return await create_movie(db_session, "Movie 1")


@pytest.fixture
async def pending_order(db_session, user, movie):
    return await create_order(db_session, user, [movie])

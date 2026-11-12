from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.interactions.models import Rating
from src.interactions.services.ratings import create_rating


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    db.execute.return_value = result
    return db, result


async def test_create_rating(mock_db):
    db, result = mock_db
    result.scalar_one_or_none.return_value = None

    rating = await create_rating(
        db=db,
        user_id=1,
        movie_id=10,
        score=8,
    )

    assert isinstance(rating, Rating)
    assert rating.user_id == 1
    assert rating.movie_id == 10
    assert rating.score == 8
    db.add.assert_called_once_with(rating)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(rating)


async def test_update_rating(mock_db):
    db, result = mock_db
    existing_rating = SimpleNamespace(score=5)
    result.scalar_one_or_none.return_value = existing_rating

    rating = await create_rating(
        db=db,
        user_id=1,
        movie_id=10,
        score=9,
    )

    assert rating is existing_rating
    assert rating.score == 9
    db.add.assert_not_called()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(rating)

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from src.interactions.schemas import RatingCreate

from src.interactions.models import Rating
from src.interactions.services.ratings import (
    create_rating,
    get_average_rating,
)


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


async def test_get_average_rating(mock_db):
    db, result = mock_db
    result.scalar_one.return_value = 8.5

    average = await get_average_rating(db=db, movie_id=10)

    assert average == 8.5
    db.execute.assert_awaited_once()


async def test_get_average_rating_without_ratings(mock_db):
    db, result = mock_db
    result.scalar_one.return_value = None

    average = await get_average_rating(db=db, movie_id=10)

    assert average is None
    db.execute.assert_awaited_once()


@pytest.mark.parametrize("score", [0, 11, -1, 100])
def test_rating_score_out_of_range(score):
    with pytest.raises(ValidationError):
        RatingCreate(movie_id=10, score=score)

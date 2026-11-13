from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.interactions.models import MovieReaction
from src.interactions.services.reactions import (
    get_movie_likes_count,
    toggle_movie_reaction,
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    db.execute.return_value = result
    return db, result


@pytest.mark.parametrize("is_like", [True, False])
async def test_create_movie_reaction(mock_db, is_like):
    db, result = mock_db
    result.scalar_one_or_none.return_value = None

    reaction = await toggle_movie_reaction(
        db=db,
        user_id=1,
        movie_id=10,
        is_like=is_like,
    )

    assert isinstance(reaction, MovieReaction)
    assert reaction.user_id == 1
    assert reaction.movie_id == 10
    assert reaction.is_like is is_like
    db.add.assert_called_once_with(reaction)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(reaction)


@pytest.mark.parametrize("existing_is_like", [True, False])
async def test_remove_same_movie_reaction(mock_db, existing_is_like):
    db, result = mock_db
    existing_reaction = SimpleNamespace(is_like=existing_is_like)
    result.scalar_one_or_none.return_value = existing_reaction

    reaction = await toggle_movie_reaction(
        db=db,
        user_id=1,
        movie_id=10,
        is_like=existing_is_like,
    )

    assert reaction is None
    db.delete.assert_awaited_once_with(existing_reaction)
    db.commit.assert_awaited_once()
    db.refresh.assert_not_awaited()


async def test_change_like_to_dislike(mock_db):
    db, result = mock_db
    existing_reaction = SimpleNamespace(is_like=True)
    result.scalar_one_or_none.return_value = existing_reaction

    reaction = await toggle_movie_reaction(
        db=db,
        user_id=1,
        movie_id=10,
        is_like=False,
    )

    assert reaction is existing_reaction
    assert reaction.is_like is False
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(reaction)


async def test_change_dislike_to_like(mock_db):
    db, result = mock_db
    existing_reaction = SimpleNamespace(is_like=False)
    result.scalar_one_or_none.return_value = existing_reaction

    reaction = await toggle_movie_reaction(
        db=db,
        user_id=1,
        movie_id=10,
        is_like=True,
    )

    assert reaction is existing_reaction
    assert reaction.is_like is True
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(reaction)


async def test_get_movie_likes_count(mock_db):
    db, result = mock_db
    result.scalar_one.return_value = 2

    likes_count = await get_movie_likes_count(db=db, movie_id=10)

    assert likes_count == 2
    db.execute.assert_awaited_once()

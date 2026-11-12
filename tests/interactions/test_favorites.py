from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import ConflictError, NotFoundError
from src.interactions.models import Favorite
from src.interactions.services.favorites import (
    add_favorite,
    remove_favorite,
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    db.execute.return_value = result
    return db, result


async def test_add_favorite(mock_db):
    db, result = mock_db
    result.scalar_one_or_none.return_value = None

    favorite = await add_favorite(
        db=db,
        user_id=1,
        movie_id=10,
    )

    assert isinstance(favorite, Favorite)
    assert favorite.user_id == 1
    assert favorite.movie_id == 10

    db.add.assert_called_once_with(favorite)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(favorite)


async def test_add_existing_favorite(mock_db):
    db, result = mock_db
    existing_favorite = SimpleNamespace(
        user_id=1,
        movie_id=10,
    )
    result.scalar_one_or_none.return_value = existing_favorite

    with pytest.raises(ConflictError):
        await add_favorite(
            db=db,
            user_id=1,
            movie_id=10,
        )

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


async def test_remove_favorite(mock_db):
    db, result = mock_db
    favorite = SimpleNamespace(
        user_id=1,
        movie_id=10,
    )
    result.scalar_one_or_none.return_value = favorite

    await remove_favorite(
        db=db,
        user_id=1,
        movie_id=10,
    )

    db.delete.assert_awaited_once_with(favorite)
    db.commit.assert_awaited_once()


async def test_remove_nonexistent_favorite(mock_db):
    db, result = mock_db
    result.scalar_one_or_none.return_value = None

    with pytest.raises(NotFoundError):
        await remove_favorite(
            db=db,
            user_id=1,
            movie_id=10,
        )

    db.delete.assert_not_awaited()
    db.commit.assert_not_awaited()

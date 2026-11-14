from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from src.accounts.models import User, UserGroup
from src.core.exceptions import ConflictError, NotFoundError
from src.core.pagination import PaginationParams
from src.interactions.models import Favorite
from src.interactions.services.favorites import (
    add_favorite,
    list_favorites,
    remove_favorite,
)
from src.movies.filters import MovieFilterParams
from src.movies.models import Certification, Movie


async def create_test_movie(db_session, name: str):
    result = await db_session.execute(select(Certification).where(Certification.name == "PG-13"))
    certification = result.scalar_one_or_none()

    if certification is None:
        certification = Certification(name="PG-13")
        db_session.add(certification)
        await db_session.flush()

    movie = Movie(
        name=name,
        year=2024,
        time=120,
        imdb=8.5,
        votes=1000,
        description="Test movie description",
        price=9.99,
        certification_id=certification.id,
    )
    db_session.add(movie)
    await db_session.flush()

    return movie


async def create_test_user(db_session, email: str):
    result = await db_session.execute(select(UserGroup).where(UserGroup.name == "USER"))
    user_group = result.scalar_one_or_none()

    if user_group is None:
        user_group = UserGroup(name="USER")
        db_session.add(user_group)
        await db_session.flush()

    user = User(
        email=email,
        hashed_password="password",
        group_id=user_group.id,
    )
    db_session.add(user)
    await db_session.flush()

    return user


def create_movie_filters(search=None):
    """Create movie filters for tests."""
    return MovieFilterParams(
        search=search,
        genre_id=None,
        year_from=None,
        year_to=None,
        min_imdb=None,
        sort_by="name",
        sort_order="asc",
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


@pytest.mark.asyncio
async def test_list_favorites_returns_user_favorites(db_session):
    user = await create_test_user(db_session, "favorites@example.com")

    movie1 = await create_test_movie(db_session, "Movie 1")
    movie2 = await create_test_movie(db_session, "Movie 2")

    db_session.add_all(
        [
            Favorite(user_id=user.id, movie_id=movie1.id),
            Favorite(user_id=user.id, movie_id=movie2.id),
        ]
    )
    await db_session.commit()

    result, total = await list_favorites(
        db_session,
        user.id,
        create_movie_filters(),
        PaginationParams(page=1, per_page=20),
    )

    assert total == 2
    assert {movie.id for movie in result} == {movie1.id, movie2.id}


@pytest.mark.asyncio
async def test_list_favorites_returns_empty_list(db_session):
    user = await create_test_user(db_session, "empty@example.com")

    result, total = await list_favorites(
        db_session,
        user.id,
        create_movie_filters(),
        PaginationParams(page=1, per_page=20),
    )

    assert result == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_favorites_returns_only_current_user_favorites(db_session):
    user1 = await create_test_user(db_session, "user1@example.com")
    user2 = await create_test_user(db_session, "user2@example.com")

    movie1 = await create_test_movie(db_session, "Movie 1")
    movie2 = await create_test_movie(db_session, "Movie 2")

    db_session.add_all(
        [
            Favorite(user_id=user1.id, movie_id=movie1.id),
            Favorite(user_id=user2.id, movie_id=movie2.id),
        ]
    )
    await db_session.commit()

    result, total = await list_favorites(
        db_session,
        user1.id,
        create_movie_filters(),
        PaginationParams(page=1, per_page=20),
    )

    assert total == 1
    assert len(result) == 1
    assert result[0].id == movie1.id


@pytest.mark.asyncio
async def test_list_favorites_applies_search_filter(db_session):
    user = await create_test_user(db_session, "search@example.com")

    movie1 = await create_test_movie(db_session, "Batman")
    movie2 = await create_test_movie(db_session, "Superman")

    db_session.add_all(
        [
            Favorite(user_id=user.id, movie_id=movie1.id),
            Favorite(user_id=user.id, movie_id=movie2.id),
        ]
    )
    await db_session.commit()

    result, total = await list_favorites(
        db_session,
        user.id,
        create_movie_filters(search="Batman"),
        PaginationParams(page=1, per_page=20),
    )

    assert total == 1
    assert len(result) == 1
    assert result[0].name == "Batman"


@pytest.mark.asyncio
async def test_list_favorites_applies_pagination(db_session):
    user = await create_test_user(db_session, "pagination@example.com")

    movies = [await create_test_movie(db_session, f"Movie {i}") for i in range(3)]

    db_session.add_all([Favorite(user_id=user.id, movie_id=movie.id) for movie in movies])
    await db_session.commit()

    result, total = await list_favorites(
        db_session,
        user.id,
        create_movie_filters(),
        PaginationParams(page=1, per_page=2),
    )

    assert total == 3
    assert len(result) == 2
    assert [movie.name for movie in result] == ["Movie 0", "Movie 1"]


@pytest.mark.asyncio
async def test_list_favorites_applies_year_filter(db_session):
    user = await create_test_user(db_session, "year-filter@example.com")

    movie1 = await create_test_movie(db_session, "Old Movie")
    movie2 = await create_test_movie(db_session, "New Movie")

    movie1.year = 2020
    movie2.year = 2024

    db_session.add_all(
        [
            Favorite(user_id=user.id, movie_id=movie1.id),
            Favorite(user_id=user.id, movie_id=movie2.id),
        ]
    )
    await db_session.commit()

    filters = create_movie_filters()
    filters.year_from = 2023

    result, total = await list_favorites(
        db_session,
        user.id,
        filters,
        PaginationParams(page=1, per_page=20),
    )

    assert total == 1
    assert len(result) == 1
    assert result[0].name == "New Movie"


@pytest.mark.asyncio
async def test_list_favorites_applies_sorting(db_session):
    user = await create_test_user(db_session, "sorting@example.com")

    movie1 = await create_test_movie(db_session, "Batman")
    movie2 = await create_test_movie(db_session, "Superman")
    movie3 = await create_test_movie(db_session, "Avengers")

    db_session.add_all(
        [
            Favorite(user_id=user.id, movie_id=movie1.id),
            Favorite(user_id=user.id, movie_id=movie2.id),
            Favorite(user_id=user.id, movie_id=movie3.id),
        ]
    )
    await db_session.commit()

    filters = create_movie_filters()
    filters.sort_by = "name"
    filters.sort_order = "desc"

    result, total = await list_favorites(
        db_session,
        user.id,
        filters,
        PaginationParams(page=1, per_page=20),
    )

    assert total == 3
    assert [movie.name for movie in result] == [
        "Superman",
        "Batman",
        "Avengers",
    ]

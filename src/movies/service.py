"""Business logic of the movies domain.

Layer rules (same for every domain):
- Functions take ``db: AsyncSession`` as the first argument.
- All SQL queries and ``commit()`` happen here, never in routers.
- Errors are raised as ``src.core.exceptions`` (NotFoundError, ConflictError, ...).
- Return ORM objects; converting to schemas is the router's job.
"""

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ConflictError, NotFoundError
from src.core.pagination import PaginationParams, paginate
from src.movies.models import Genre, Movie
from src.movies.schemas import GenreCreate, GenreUpdate
from src.movies.filters import MovieFilterParams, apply_movie_filters


# --- GENRES SERVICE ---


async def list_genres(db: AsyncSession, pagination: PaginationParams) -> tuple[list[Any], int]:
    """Return a page of genres ordered by name and the total count."""
    stmt = select(Genre).order_by(Genre.name)
    return await paginate(db, stmt, pagination)


async def get_genre(db: AsyncSession, genre_id: int) -> Genre:
    """Return a genre by id.

    Raises:
        NotFoundError: genre does not exist.
    """
    genre = await db.get(Genre, genre_id)
    if genre is None:
        raise NotFoundError(f"Genre with id={genre_id} not found")
    return genre


async def _ensure_name_is_free(db: AsyncSession, name: str) -> None:
    exists = await db.scalar(select(Genre.id).where(Genre.name == name))
    if exists is not None:
        raise ConflictError(f"Genre '{name}' already exists")


async def create_genre(db: AsyncSession, data: GenreCreate) -> Genre:
    """Create a genre with uniqueness check before commit.

    Raises:
        ConflictError: a genre with the same name already exists.
    """
    if not data.name:
        raise ConflictError("Genre name cannot be empty")

    await _ensure_name_is_free(db, data.name)
    genre = Genre(**data.model_dump())
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    return genre


async def update_genre(db: AsyncSession, genre_id: int, data: GenreUpdate) -> Genre:
    """Partially update a genre, preventing null values for name.

    Raises:
        NotFoundError: genre does not exist.
        ConflictError: new name is taken or null.
    """
    genre = await get_genre(db, genre_id)
    changes = data.model_dump(exclude_unset=True)

    if "name" in changes:
        if changes["name"] is None:
            raise ConflictError("Genre name cannot be null")
        if changes["name"] != genre.name:
            await _ensure_name_is_free(db, changes["name"])

    for field, value in changes.items():
        setattr(genre, field, value)

    await db.commit()
    await db.refresh(genre)
    return genre


async def delete_genre(db: AsyncSession, genre_id: int) -> None:
    """Delete a genre.

    Raises:
        NotFoundError: genre does not exist.
    """
    genre = await get_genre(db, genre_id)
    await db.delete(genre)
    await db.commit()


# --- MOVIES SERVICE ---


async def get_movie(db: AsyncSession, movie_id: int) -> Movie:
    """Retrieve a single movie by its ID with all relations loaded via selectinload.

    Raises:
        NotFoundError: if the movie does not exist.
    """
    stmt = (
        select(Movie)
        .options(
            selectinload(Movie.genres),
            selectinload(Movie.stars),
            selectinload(Movie.directors),
            selectinload(Movie.certification),
        )
        .where(Movie.id == movie_id)
    )
    result = await db.execute(stmt)
    movie = result.scalar_one_or_none()

    if not movie:
        raise NotFoundError(f"Movie with ID {movie_id} not found")

    return movie


async def list_movies(
    db: AsyncSession, filter_params: MovieFilterParams, pagination_params: PaginationParams
) -> tuple[list[Any], int]:
    """Retrieve a paginated, filtered, and searched list of movies with relations loaded."""
    stmt = select(Movie).options(
        selectinload(Movie.genres),
        selectinload(Movie.stars),
        selectinload(Movie.directors),
        selectinload(Movie.certification),
    )

    stmt = apply_movie_filters(stmt, filter_params)

    return await paginate(db, stmt, pagination_params)

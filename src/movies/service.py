"""Business logic of the movies domain.

Layer rules (same for every domain):
    * Functions take ``db: AsyncSession`` as the first argument.
    * All SQL queries and ``commit()`` happen here, never in routers.
    * Errors are raised as ``src.core.exceptions`` (NotFoundError, ConflictError, ...).
    * Return ORM objects; converting to schemas is the router's job.
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.core.pagination import PaginationParams, paginate
from src.movies.models import Genre
from src.movies.schemas import GenreCreate, GenreUpdate


async def list_genres(db: AsyncSession, pagination: PaginationParams) -> tuple[list[Any], int]:
    """Return a page of genres ordered by name and the total count.

    TODO(P4): spec also requires the number of movies per genre (COUNT + GROUP BY).
    """
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
    """Create a genre.

    Raises:
        ConflictError: a genre with the same name already exists.
    """
    await _ensure_name_is_free(db, data.name)
    genre = Genre(**data.model_dump())
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    return genre


async def update_genre(db: AsyncSession, genre_id: int, data: GenreUpdate) -> Genre:
    """Partially update a genre (only fields that were sent).

    Raises:
        NotFoundError: genre does not exist.
        ConflictError: new name is taken by another genre.
    """
    genre = await get_genre(db, genre_id)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] != genre.name:
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

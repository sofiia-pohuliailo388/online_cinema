"""Business logic for movie favorites."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import ConflictError, NotFoundError
from src.core.pagination import PaginationParams, paginate
from src.interactions.models import Favorite
from src.movies.filters import MovieFilterParams, apply_movie_filters
from src.movies.models import Movie


async def add_favorite(
    db: AsyncSession,
    user_id: int,
    movie_id: int,
) -> Favorite:
    """Add a movie to the user's favorites."""
    stmt = select(Favorite).where(
        Favorite.user_id == user_id,
        Favorite.movie_id == movie_id,
    )
    result = await db.execute(stmt)
    favorite = result.scalar_one_or_none()

    if favorite is not None:
        raise ConflictError("Movie is already in favorites")

    favorite = Favorite(user_id=user_id, movie_id=movie_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    return favorite


async def remove_favorite(
    db: AsyncSession,
    user_id: int,
    movie_id: int,
) -> None:
    """Remove a movie from the user's favorites."""
    stmt = select(Favorite).where(
        Favorite.user_id == user_id,
        Favorite.movie_id == movie_id,
    )
    result = await db.execute(stmt)
    favorite = result.scalar_one_or_none()

    if favorite is None:
        raise NotFoundError("Favorite not found")

    await db.delete(favorite)
    await db.commit()


async def list_favorites(
    db: AsyncSession,
    user_id: int,
    filters: MovieFilterParams,
    pagination: PaginationParams,
) -> tuple[list[Movie], int]:
    """Return the user's filtered and paginated favorite movies."""
    stmt = (
        select(Movie)
        .join(Favorite)
        .where(Favorite.user_id == user_id)
        .options(
            selectinload(Movie.genres),
            selectinload(Movie.stars),
            selectinload(Movie.directors),
            selectinload(Movie.certification),
        )
    )

    stmt = apply_movie_filters(stmt, filters)

    return await paginate(db, stmt, pagination)

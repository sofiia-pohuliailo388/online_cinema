"""Business logic for movie favorites."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ConflictError, NotFoundError
from src.interactions.models import Favorite


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

    favorite = Favorite(
        user_id=user_id,
        movie_id=movie_id,
    )
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


async def list_favorites(...):
    """Get the user's favorite movies."""
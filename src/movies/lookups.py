from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.movies.models import Movie


async def ensure_movie_exists(db: AsyncSession, movie_id: int) -> None:
    """Ensure that a movie exists."""
    stmt = select(Movie.id).where(Movie.id == movie_id)
    result = await db.execute(stmt)

    if result.scalar_one_or_none() is None:
        raise NotFoundError("Movie not found")

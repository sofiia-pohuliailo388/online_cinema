"""Business logic for movie ratings."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.interactions.models import Rating
from src.movies.lookups import ensure_movie_exists


async def create_rating(
    db: AsyncSession,
    user_id: int,
    movie_id: int,
    score: int,
) -> Rating:
    """Create or update a user's rating for a movie."""

    await ensure_movie_exists(db, movie_id)

    stmt = select(Rating).where(
        Rating.user_id == user_id,
        Rating.movie_id == movie_id,
    )
    result = await db.execute(stmt)
    rating = result.scalar_one_or_none()

    if rating is None:
        rating = Rating(
            user_id=user_id,
            movie_id=movie_id,
            score=score,
        )
        db.add(rating)
    else:
        rating.score = score

    await db.commit()
    await db.refresh(rating)

    return rating


async def get_average_rating(db: AsyncSession, movie_id: int) -> float | None:
    """Calculate the average rating for a movie."""
    stmt = select(func.avg(Rating.score)).where(Rating.movie_id == movie_id)
    result = await db.execute(stmt)
    average = result.scalar_one()

    return round(float(average), 2) if average is not None else None

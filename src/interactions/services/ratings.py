"""Business logic for movie ratings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.interactions.models import Rating


async def create_rating(
    db: AsyncSession,
    user_id: int,
    movie_id: int,
    score: int,
) -> Rating:
    """Create or update a user's rating for a movie."""

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

"""Business logic for movie likes and dislikes."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.interactions.models import MovieReaction
from src.movies.lookups import ensure_movie_exists


async def toggle_movie_reaction(
    db: AsyncSession,
    user_id: int,
    movie_id: int,
    is_like: bool,
) -> MovieReaction | None:
    """Create, change, or remove a movie reaction."""

    await ensure_movie_exists(db, movie_id)

    stmt = select(MovieReaction).where(
        MovieReaction.user_id == user_id,
        MovieReaction.movie_id == movie_id,
    )
    result = await db.execute(stmt)
    reaction = result.scalar_one_or_none()

    if reaction is None:
        reaction = MovieReaction(
            user_id=user_id,
            movie_id=movie_id,
            is_like=is_like,
        )
        db.add(reaction)
    elif reaction.is_like == is_like:
        await db.delete(reaction)
        reaction = None
    else:
        reaction.is_like = is_like

    await db.commit()

    if reaction is not None:
        await db.refresh(reaction)

    return reaction


async def get_movie_likes_count(db: AsyncSession, movie_id: int) -> int:
    """Count positive reactions for a movie."""
    stmt = select(func.count(MovieReaction.id)).where(
        MovieReaction.movie_id == movie_id,
        MovieReaction.is_like.is_(True),
    )
    result = await db.execute(stmt)

    return result.scalar_one()

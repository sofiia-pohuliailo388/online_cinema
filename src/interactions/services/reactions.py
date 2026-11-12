"""Business logic for movie likes and dislikes."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.interactions.models import MovieReaction


async def toggle_movie_reaction(
    db: AsyncSession,
    user_id: int,
    movie_id: int,
    is_like: bool,
) -> MovieReaction | None:
    """Create, change, or remove a movie reaction."""

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

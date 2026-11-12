"""Business logic of the orders domain (owner: P6)."""

from sqlalchemy.ext.asyncio import AsyncSession


async def is_movie_purchased(db: AsyncSession, user_id: int, movie_id: int) -> bool:
    """CONTRACT: has the user a PAID order containing this movie?

    TODO(P6): real query. Stub returns False.
    """
    return False


async def is_movie_purchased_by_anyone(db: AsyncSession, movie_id: int) -> bool:
    """CONTRACT for P4: forbid deleting a movie that somebody has bought.

    TODO(P6): real query. Stub returns False.
    """
    return False


async def mark_order_paid(db: AsyncSession, order_id: int) -> None:
    """CONTRACT for P7: set status to ``paid`` and remove paid movies from the user's cart.

    Called from the Stripe webhook. Must be idempotent (safe to call twice).
    TODO(P6): implement.
    """
    raise NotImplementedError

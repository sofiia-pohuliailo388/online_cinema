"""Business logic of the cart domain (owner: P6)."""

from sqlalchemy.ext.asyncio import AsyncSession


async def is_movie_in_carts(db: AsyncSession, movie_id: int) -> bool:
    """CONTRACT for P4: is the movie in at least one user's cart?

    Used to warn a moderator before deleting a movie.
    TODO(P6): real query. Stub returns False.
    """
    return False

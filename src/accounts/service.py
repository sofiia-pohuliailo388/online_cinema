"""Business logic of the accounts domain (spec, section 1)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.models import User


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Return a user by id with the group already loaded.

    Args:
        db: Database session.
        user_id: Id of the user to find.

    Returns:
        The user (with ``user.group`` loaded), or ``None`` if there is no such user.
    """
    result = await db.execute(
        select(User).options(selectinload(User.group)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

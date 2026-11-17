"""Admin management of users (spec, section 1): list, change group, manual activation.

Owner: P3.
"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.enums import UserGroupEnum
from src.accounts.models import ActivationToken, User, UserGroup
from src.accounts.service import get_user_by_id
from src.core.exceptions import ConflictError, NotFoundError
from src.core.pagination import PaginationParams, paginate


async def list_users(
    db: AsyncSession,
    pagination: PaginationParams,
    group: UserGroupEnum | None = None,
    is_active: bool | None = None,
    email: str | None = None,
) -> tuple[list[User], int]:
    """Return a page of users (ordered by id) with optional filters."""
    stmt = select(User).options(selectinload(User.group)).order_by(User.id)
    if group is not None:
        stmt = stmt.join(User.group).where(UserGroup.name == group)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if email:
        stmt = stmt.where(User.email.ilike(f"%{email}%"))
    return await paginate(db, stmt, pagination)


async def get_user(db: AsyncSession, user_id: int) -> User:
    """Return a user with the group loaded.

    Raises:
        NotFoundError: the user does not exist.
    """
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise NotFoundError(f"User with id={user_id} not found")
    return user


async def change_user_group(
    db: AsyncSession, admin_id: int, user_id: int, group: UserGroupEnum
) -> User:
    """Move the user to another group.

    Raises:
        ConflictError: an admin tries to change their own group (they could lock themselves out).
        NotFoundError: the user does not exist.
    """
    if user_id == admin_id:
        raise ConflictError("Admins cannot change their own group")

    user = await get_user(db, user_id)
    user_group = await db.scalar(select(UserGroup).where(UserGroup.name == group))
    if user_group is None:
        user_group = UserGroup(name=group)
        db.add(user_group)
        await db.flush()

    user.group_id = user_group.id
    await db.commit()
    await db.refresh(user, ["group"])
    return user


async def activate_user_manually(db: AsyncSession, user_id: int) -> User:
    """Activate the account without the email link and delete its activation token.

    Activating an already active account is not an error.

    Raises:
        NotFoundError: the user does not exist.
    """
    user = await get_user(db, user_id)
    user.is_active = True
    await db.execute(delete(ActivationToken).where(ActivationToken.user_id == user_id))
    await db.commit()
    await db.refresh(user, ["group"])
    return user

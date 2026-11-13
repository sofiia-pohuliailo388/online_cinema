"""Auth dependencies - CONTRACT used by every domain (owner: P2).

Do not change these signatures without telling the team.

Usage::

    from src.accounts.dependencies import CurrentUser, require_roles
    from src.accounts.enums import UserGroupEnum

    @router.get("/cart")
    async def get_cart(user: CurrentUser, db: DbSession) -> CartRead: ...

    @router.post("/genres", dependencies=[Depends(require_roles(UserGroupEnum.MODERATOR))])
    async def create_genre(...): ...

The returned user object must expose ``user.id`` and ``user.group.name`` (a ``UserGroupEnum``).
In tests use the ``login_as`` fixture from ``tests/conftest.py`` instead of real tokens.
"""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.accounts.enums import UserGroupEnum
from src.accounts.models import User
from src.accounts.security import decode_token
from src.accounts.service import get_user_by_id
from src.core.database import DbSession
from src.core.exceptions import PermissionDeniedError, UnauthorizedError

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Return the authenticated, active user.

    Reads the ``Authorization: Bearer <access>`` header, decodes the JWT
    (payload ``{"user_id", "group", "exp"}``) and loads the user together with the group.

    Args:
        db: Database session.
        credentials: Parsed ``Authorization`` header, or ``None`` if it is missing.

    Returns:
        The authenticated user with ``user.group`` loaded.

    Raises:
        UnauthorizedError: If the header is missing, the token is invalid or expired,
            the user does not exist or the account is not activated.
    """
    if credentials is None:
        raise UnauthorizedError("Not authenticated")

    payload = decode_token(credentials.credentials)

    user_id = payload.get("user_id")
    if type(user_id) is not int:
        raise UnauthorizedError("Invalid token payload")

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user


def require_roles(*groups: UserGroupEnum) -> Callable[..., Awaitable[Any]]:
    """Dependency factory: allow access only to users from ``groups``.

    ADMIN is always allowed, because it inherits all permissions (spec, section 1).
    """
    allowed = {*groups, UserGroupEnum.ADMIN}

    async def checker(user: Any = Depends(get_current_user)) -> Any:
        if user.group.name not in allowed:
            raise PermissionDeniedError("Not enough permissions")
        return user

    return checker


CurrentUser = Annotated[Any, Depends(get_current_user)]
ModeratorUser = Annotated[Any, Depends(require_roles(UserGroupEnum.MODERATOR))]
AdminUser = Annotated[Any, Depends(require_roles(UserGroupEnum.ADMIN))]

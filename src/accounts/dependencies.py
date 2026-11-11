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

from src.accounts.enums import UserGroupEnum
from src.core.exceptions import PermissionDeniedError, UnauthorizedError


async def get_current_user() -> Any:
    """Return the authenticated, active user.

    TODO(P2): read ``Authorization: Bearer <access>`` header, decode JWT
    (payload ``{"user_id", "group", "exp"}``), load ``User`` with ``selectinload(User.group)``,
    raise ``UnauthorizedError`` if the token is invalid/expired or the user is inactive.
    """
    raise UnauthorizedError("Authentication is not implemented yet")


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

"""Admin endpoints for managing users (spec, section 1). Admin only. Owner: P3."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.accounts import admin_service
from src.accounts.dependencies import AdminUser
from src.accounts.enums import UserGroupEnum
from src.accounts.user_schemas import AdminUserRead, ChangeGroupRequest
from src.core.database import DbSession
from src.core.exceptions import ErrorResponse, Responses
from src.core.pagination import Page, PaginationParams

router = APIRouter(prefix="/admin/users", tags=["admin"])

ADMIN_ONLY: Responses = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Admin only"},
}
NOT_FOUND: Responses = {404: {"model": ErrorResponse, "description": "User not found"}}


@router.get("", responses=ADMIN_ONLY)
async def list_users(
    db: DbSession,
    _: AdminUser,
    pagination: Annotated[PaginationParams, Depends()],
    group: Annotated[UserGroupEnum | None, Query(description="Only users of this group")] = None,
    is_active: Annotated[bool | None, Query(description="Only (in)active users")] = None,
    email: Annotated[str | None, Query(description="Part of the email")] = None,
) -> Page[AdminUserRead]:
    """List users with optional filters by group, activation status and email."""
    users, total = await admin_service.list_users(db, pagination, group, is_active, email)
    return Page[AdminUserRead].create(
        [AdminUserRead.from_user(u) for u in users], total, pagination
    )


@router.get("/{user_id}", responses={**ADMIN_ONLY, **NOT_FOUND})
async def get_user(user_id: int, db: DbSession, _: AdminUser) -> AdminUserRead:
    """Get one user."""
    user = await admin_service.get_user(db, user_id)
    return AdminUserRead.from_user(user)


@router.patch(
    "/{user_id}/group",
    responses={
        **ADMIN_ONLY,
        **NOT_FOUND,
        409: {"model": ErrorResponse, "description": "Admin cannot change own group"},
    },
)
async def change_user_group(
    user_id: int, data: ChangeGroupRequest, db: DbSession, admin: AdminUser
) -> AdminUserRead:
    """Move a user to another group: USER, MODERATOR or ADMIN."""
    user = await admin_service.change_user_group(db, admin.id, user_id, data.group)
    return AdminUserRead.from_user(user)


@router.post("/{user_id}/activate", responses={**ADMIN_ONLY, **NOT_FOUND})
async def activate_user(user_id: int, db: DbSession, _: AdminUser) -> AdminUserRead:
    """Activate an account manually, without the email link."""
    user = await admin_service.activate_user_manually(db, user_id)
    return AdminUserRead.from_user(user)

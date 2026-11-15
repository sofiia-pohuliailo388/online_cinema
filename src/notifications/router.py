"""HTTP endpoints of in-app notifications (spec, section 2). Owner: P3.

Notifications are created by ``notify_user`` (e.g. a reply or a like on your comment).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.accounts.dependencies import CurrentUser
from src.core.database import DbSession
from src.core.exceptions import ErrorResponse, Responses
from src.core.pagination import Page, PaginationParams
from src.notifications import service
from src.notifications.schemas import MarkedReadRead, NotificationRead, UnreadCountRead

router = APIRouter(prefix="/notifications", tags=["notifications"])

UNAUTHORIZED: Responses = {401: {"model": ErrorResponse, "description": "Not authenticated"}}
NOT_FOUND: Responses = {404: {"model": ErrorResponse, "description": "Notification not found"}}


@router.get("", responses=UNAUTHORIZED)
async def list_my_notifications(
    db: DbSession,
    user: CurrentUser,
    pagination: Annotated[PaginationParams, Depends()],
    unread_only: Annotated[bool, Query(description="Only unread notifications")] = False,
) -> Page[NotificationRead]:
    """List the current user's notifications, newest first."""
    items, total = await service.list_notifications(db, user.id, pagination, unread_only)
    return Page[NotificationRead].create(
        [NotificationRead.model_validate(n) for n in items], total, pagination
    )


@router.get("/unread-count", responses=UNAUTHORIZED)
async def my_unread_count(db: DbSession, user: CurrentUser) -> UnreadCountRead:
    """Number of unread notifications (e.g. for a badge in the UI)."""
    return UnreadCountRead(unread=await service.count_unread(db, user.id))


@router.patch("/{notification_id}/read", responses={**UNAUTHORIZED, **NOT_FOUND})
async def mark_notification_read(
    notification_id: int, db: DbSession, user: CurrentUser
) -> NotificationRead:
    """Mark one of your notifications as read."""
    notification = await service.mark_as_read(db, user.id, notification_id)
    return NotificationRead.model_validate(notification)


@router.post("/read-all", responses=UNAUTHORIZED)
async def mark_all_notifications_read(db: DbSession, user: CurrentUser) -> MarkedReadRead:
    """Mark all of your notifications as read."""
    return MarkedReadRead(updated=await service.mark_all_as_read(db, user.id))

"""HTTP endpoints of the current user's profile and avatar (spec, section 1). Owner: P3."""

from typing import Any

from fastapi import APIRouter, UploadFile, status

from src.accounts import profile_service
from src.accounts.dependencies import CurrentUser
from src.accounts.user_schemas import ProfileRead, ProfileUpdate
from src.core.database import DbSession
from src.core.exceptions import ErrorResponse
from src.storage import s3

router = APIRouter(prefix="/users/me/profile", tags=["profile"])

UNAUTHORIZED = {401: {"model": ErrorResponse, "description": "Not authenticated"}}
BAD_AVATAR = {400: {"model": ErrorResponse, "description": "Not an image, empty or > 2 MB"}}
STORAGE_DOWN = {503: {"model": ErrorResponse, "description": "File storage is unavailable"}}


def _to_read(profile: Any) -> ProfileRead:
    return ProfileRead(
        first_name=profile.first_name,
        last_name=profile.last_name,
        gender=profile.gender,
        date_of_birth=profile.date_of_birth,
        info=profile.info,
        avatar_url=s3.get_file_url(profile.avatar) if profile.avatar else None,
    )


@router.get("", responses=UNAUTHORIZED)
async def get_my_profile(db: DbSession, user: CurrentUser) -> ProfileRead:
    """Get the current user's profile. An empty profile is created on first access."""
    profile = await profile_service.get_or_create_profile(db, user.id)
    return _to_read(profile)


@router.patch("", responses=UNAUTHORIZED)
async def update_my_profile(data: ProfileUpdate, db: DbSession, user: CurrentUser) -> ProfileRead:
    """Change profile fields. Only the sent fields change; a field sent as null is cleared."""
    profile = await profile_service.update_profile(db, user.id, data)
    return _to_read(profile)


@router.put("/avatar", responses={**UNAUTHORIZED, **BAD_AVATAR, **STORAGE_DOWN})
async def upload_my_avatar(file: UploadFile, db: DbSession, user: CurrentUser) -> ProfileRead:
    """Upload a new avatar: a JPEG, PNG or WebP image up to 2 MB. Replaces the old one."""
    data = await file.read(profile_service.AVATAR_MAX_BYTES + 1)
    profile = await profile_service.set_avatar(db, user.id, data, file.content_type)
    return _to_read(profile)


@router.delete(
    "/avatar", status_code=status.HTTP_204_NO_CONTENT, responses={**UNAUTHORIZED, **STORAGE_DOWN}
)
async def delete_my_avatar(db: DbSession, user: CurrentUser) -> None:
    """Remove the avatar."""
    await profile_service.delete_avatar(db, user.id)

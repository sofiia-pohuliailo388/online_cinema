"""User profile and avatar (spec, section 1: UserProfile). Owner: P3."""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import UserProfile
from src.accounts.user_schemas import ProfileUpdate
from src.core.exceptions import BadRequestError
from src.storage import s3

logger = logging.getLogger(__name__)

AVATAR_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
AVATAR_MAX_BYTES = 2 * 1024 * 1024


async def get_or_create_profile(db: AsyncSession, user_id: int) -> UserProfile:
    """Return the user's profile, creating an empty one on first access."""
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user_id))
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


async def update_profile(db: AsyncSession, user_id: int, data: ProfileUpdate) -> UserProfile:
    """Change only the fields that were sent (a field sent as ``null`` is cleared)."""
    profile = await get_or_create_profile(db, user_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    await db.commit()
    await db.refresh(profile)
    return profile


async def set_avatar(
    db: AsyncSession, user_id: int, data: bytes, content_type: str | None
) -> UserProfile:
    """Upload a new avatar and remove the previous one from the storage.

    Raises:
        BadRequestError: not a JPEG/PNG/WebP image, empty file or larger than 2 MB.
        StorageUnavailableError: the file storage is unavailable (503).
    """
    if content_type not in AVATAR_CONTENT_TYPES:
        raise BadRequestError("Avatar must be a JPEG, PNG or WebP image")
    if not data:
        raise BadRequestError("Avatar file is empty")
    if len(data) > AVATAR_MAX_BYTES:
        raise BadRequestError("Avatar must not be larger than 2 MB")

    profile = await get_or_create_profile(db, user_id)
    old_key = profile.avatar
    new_key = f"avatars/{user_id}/{uuid.uuid4().hex}.{AVATAR_CONTENT_TYPES[content_type]}"

    await s3.upload_file(new_key, data, content_type)
    profile.avatar = new_key
    await db.commit()
    await db.refresh(profile)

    if old_key:
        await _delete_quietly(old_key)
    return profile


async def delete_avatar(db: AsyncSession, user_id: int) -> UserProfile:
    """Remove the avatar from the profile and from the storage."""
    profile = await get_or_create_profile(db, user_id)
    old_key = profile.avatar
    if old_key:
        profile.avatar = None
        await db.commit()
        await db.refresh(profile)
        await _delete_quietly(old_key)
    return profile


async def _delete_quietly(key: str) -> None:
    # A leftover file in the storage is not worth failing the user's request.
    try:
        await s3.delete_file(key)
    except Exception:
        logger.warning("Could not delete old avatar %s from the storage", key, exc_info=True)

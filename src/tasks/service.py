"""Celery tasks (owner: P3).

Tasks are thin synchronous wrappers: the real work lives in plain functions,
so it can be tested without a running worker or Redis.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import src.models  # noqa: F401  (all models must be registered before any query)
from src.accounts.models import ActivationToken, PasswordResetToken
from src.core.config import settings
from src.notifications.service import deliver_email
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def send_email_task(to: str, subject: str, template: str, context: dict[str, Any]) -> None:
    """Send one email in the background (queued by ``send_email``)."""
    deliver_email(to=to, subject=subject, template=template, context=context)


async def delete_expired_tokens(db: AsyncSession) -> tuple[int, int]:
    """Delete expired activation and password-reset tokens.

    Returns:
        Number of deleted activation tokens and of deleted password-reset tokens.
    """
    now = datetime.now(timezone.utc)
    activation = await db.execute(
        delete(ActivationToken).where(ActivationToken.expires_at < now)
    )
    reset = await db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.expires_at < now)
    )
    await db.commit()
    return activation.rowcount, reset.rowcount


async def _cleanup_expired_tokens() -> tuple[int, int]:
    # A fresh engine per run: every Celery run has its own event loop (asyncio.run).
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            return await delete_expired_tokens(db)
    finally:
        await engine.dispose()


@celery_app.task
def cleanup_expired_tokens() -> None:
    """Hourly celery-beat job: remove expired activation and password-reset tokens."""
    deleted_activation, deleted_reset = asyncio.run(_cleanup_expired_tokens())
    logger.info(
        "Removed expired tokens: %s activation, %s password reset",
        deleted_activation,
        deleted_reset,
    )

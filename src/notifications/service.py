"""Notification contract (owner: P3). Stubs only log until implemented."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, template: str, context: dict[str, Any]) -> None:
    """CONTRACT: queue an email rendered from ``templates/<template>``.

    Example: ``send_email(user.email, "Activate account", "activation.html", {"link": url})``
    TODO(P3): enqueue Celery task that renders Jinja2 template and sends via SMTP.
    """
    logger.info("EMAIL to=%s subject=%s template=%s context=%s", to, subject, template, context)


async def notify_user(db: AsyncSession, user_id: int, text: str) -> None:
    """CONTRACT: create an in-app notification (e.g. reply/like on a comment).

    TODO(P3): save ``Notification`` row.
    """
    logger.info("NOTIFY user_id=%s text=%s", user_id, text)

"""Notification contract (owner: P3): emails and in-app notifications.

* ``send_email`` - CONTRACT: queue an email (Celery task) and return immediately.
* ``deliver_email`` - render the template and send it via SMTP (runs in the Celery worker).
* ``notify_user`` - CONTRACT: save an in-app ``Notification``.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.notifications.models import Notification

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)


def send_email(to: str, subject: str, template: str, context: dict[str, Any]) -> None:
    """CONTRACT: queue an email rendered from ``templates/<template>``.

    The email is sent in the background by a Celery worker, so the request is not slowed down.
    If the queue is unavailable, the error is logged and the request still succeeds.

    Example: ``send_email(user.email, "Activate account", "activation.html", {"link": url})``
    """
    # Local import: src.tasks.service imports this module, a top-level import would be circular.
    from src.tasks.service import send_email_task

    try:
        send_email_task.delay(to=to, subject=subject, template=template, context=context)
    except Exception:
        logger.exception("Failed to queue email '%s' to %s", template, to)


def deliver_email(to: str, subject: str, template: str, context: dict[str, Any]) -> None:
    """Render ``templates/<template>`` and send it via SMTP (MailHog in development).

    Raises:
        smtplib.SMTPException, OSError: the SMTP server is unavailable or rejected the email.
    """
    html_content = jinja_env.get_template(template).render(context)

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.EMAIL_FROM
    message["To"] = to
    message.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.sendmail(settings.EMAIL_FROM, [to], message.as_string())

    logger.info("Email '%s' sent to %s", template, to)


async def notify_user(db: AsyncSession, user_id: int, text: str) -> None:
    """CONTRACT: create an in-app notification (e.g. reply/like on a comment)."""
    logger.info("NOTIFY user_id=%s text=%s", user_id, text)

    try:
        db_notification = Notification(user_id=user_id, text=text, is_read=False)
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)
        logger.info(
            "Successfully saved notification ID=%s for user_id=%s", db_notification.id, user_id
        )
    except Exception as e:
        await db.rollback()
        logger.error("Failed to save notification for user_id=%s: %s", user_id, e)
        raise

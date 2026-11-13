"""Notification contract (owner: P3). Stubs only log until implemented."""
import logging
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

def send_email(to: str, subject: str, template: str, context: dict[str, Any]) -> None:
    """CONTRACT: queue an email rendered from ``templates/<template>``.

    Example: ``send_email(user.email, "Activate account", "activation.html", {"link": url})``
    TODO(P3): enqueue Celery task that renders Jinja2 template and sends via SMTP.
    """
    logger.info("EMAIL to=%s subject=%s template=%s context=%s", to, subject, template, context)

    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        html_template = jinja_env.get_template(template)
        html_content = html_template.render(context)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = "noreply@cinema.local"
        msg["To"] = to
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP("localhost", 1025) as server:
            server.sendmail(msg["From"], [to], msg.as_string())

        logger.info("[SMTP] Successfully sent email to %s via MailHog", to)
    except Exception as e:
        logger.error("[SMTP ERROR] Failed to send email to %s: %s", to, e)


async def notify_user(db: AsyncSession, user_id: int, text: str) -> None:
    """CONTRACT: create an in-app notification (e.g. reply/like on a comment).

    TODO(P3): save ``Notification`` row.
    """
    logger.info("NOTIFY user_id=%s text=%s", user_id, text)

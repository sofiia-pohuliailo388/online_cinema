from datetime import datetime, timezone
import logging

from src.tasks.celery_app import celery_app
from src.notifications.service import send_email
from src.core.database import SessionLocal
from src.accounts.models import ActivationToken, PasswordResetToken

logger = logging.getLogger(__name__)


@celery_app.task
def send_email_task(to: str, subject: str, template: str, context: dict) -> None:
    try:
        send_email(to=to, subject=subject, template=template, context=context)
    except Exception as exc:
        logger.error("Failed to send email task to %s: %s", to, exc)
        raise


@celery_app.task
def cleanup_expired_tokens() -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db = SessionLocal()
    try:
        deleted_activation = db.query(ActivationToken).filter(ActivationToken.expires_at < now).delete()
        deleted_reset = db.query(PasswordResetToken).filter(PasswordResetToken.expires_at < now).delete()
        db.commit()
        logger.info("Cleaned up expired tokens: %s activation, %s reset", deleted_activation, deleted_reset)
    except Exception as exc:
        db.rollback()
        logger.error("Error during expired tokens cleanup: %s", exc)
        raise
    finally:
        db.close()

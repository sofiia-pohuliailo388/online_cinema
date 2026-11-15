"""Celery application and celery-beat schedule (owner: P3).

Worker: ``celery -A src.tasks.celery_app worker -l info``
Beat:   ``celery -A src.tasks.celery_app beat -l info``
"""

from celery import Celery
from celery.schedules import crontab

from src.core.config import settings

celery_app = Celery(
    "cinema_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["src.tasks.service"],
)

celery_app.conf.update(
    timezone="UTC",
    task_serializer="json",
    accept_content=["json"],
)

celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens-hourly": {
        "task": "src.tasks.service.cleanup_expired_tokens",
        "schedule": crontab(minute=0),
    },
}

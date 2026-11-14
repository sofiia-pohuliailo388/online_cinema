from celery import Celery
from celery.schedules import crontab

celery_app = Celery(
    "cinema_tasks", broker="redis://localhost:6379/0", backend="redis://localhost:6379/0"
)

celery_app.autodiscover_tasks(["src.tasks"])

celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens-hourly": {
        "task": "src.tasks.service.cleanup_expired_tokens",
        "schedule": crontab(minute=0),
    },
}

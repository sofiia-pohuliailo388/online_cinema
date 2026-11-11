"""Background jobs (owner: P3): Celery app and celery-beat schedule.

Planned: ``src/tasks/celery_app.py`` with ``celery_app`` and beat schedule
(e.g. hourly removal of expired activation / password-reset tokens).
Task functions stay thin: they open a DB session and call a domain service.
"""

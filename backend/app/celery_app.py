from celery import Celery
from kombu import Queue

from app.core.config import settings

celery_app = Celery(
    "company_brain",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.brain_tasks",
        "app.tasks.personal_tasks",
    ],
)

celery_app.conf.update(
    # Queues
    task_queues=(
        Queue("brain"),
        Queue("personal"),
    ),
    task_default_queue="brain",
    task_routes={
        "app.tasks.brain_tasks.*": {"queue": "brain"},
        "app.tasks.personal_tasks.*": {"queue": "personal"},
    },

    # Reliability — tasks are not acknowledged until the worker completes them,
    # so a worker crash re-queues the task rather than silently dropping it.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Retry on broker connection failure at startup (e.g. Redis not yet ready)
    broker_connection_retry_on_startup=True,

    # beat_schedule is defined in Phase 3 once brain_tasks.scan_and_ingest
    # is implemented. Defining it here before the task exists causes workers
    # to reject every enqueued job with "unregistered task" errors.
)

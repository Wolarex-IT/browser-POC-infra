from celery import Celery
from kombu import Queue

from .config import CELERY_BROKER_URL

# include= lets the worker import the task module (and its signal handlers) at startup
# without the FastAPI app having to import the heavy browser/docker code.
# No result backend: the API polls the jobs table (Postgres is the source of truth),
# so Celery's own result store would only be dead weight to expire.
celery = Celery(
    "browser_poc",
    broker=CELERY_BROKER_URL,
    include=["service.tasks"],
)
# Ack a job only after it finishes, and requeue it if the worker dies mid-task, so a
# crash during a render redelivers the job instead of silently dropping it.
celery.conf.task_acks_late = True
celery.conf.task_reject_on_worker_lost = True
# One unacked job in flight per worker - fair dispatch since each render is heavy.
celery.conf.worker_prefetch_multiplier = 1

celery.conf.task_queues = [Queue("celery", queue_arguments={"x-queue-type": "quorum"})]
celery.conf.task_default_queue = "celery"
celery.conf.worker_detect_quorum_queues = True
celery.conf.worker_enable_remote_control = False
celery.conf.worker_send_task_events = False

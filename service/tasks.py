from celery.signals import worker_process_init, worker_process_shutdown
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .browser import spawn_browser, sweep_stale_containers
from .celery_app import celery
from .config import (
    MAX_RENDER_ATTEMPTS,
    NAV_TIMEOUT,
    NAV_WAIT_UNTIL,
    RENDER_TASK,
)
from .db import Base, SyncSessionLocal, sync_engine
from .models import Job

_worker_state: dict = {}


@worker_process_init.connect
def init_worker(**kwargs):
    """Give each Celery worker process its own CloakBrowser, reused across its tasks."""
    Base.metadata.create_all(sync_engine)
    sweep_stale_containers()
    _spawn()


@worker_process_shutdown.connect
def teardown_worker(**kwargs):
    """Close the browser and remove its container when the worker process exits."""
    _teardown()


def _spawn() -> None:
    container, driver, browser = spawn_browser()
    _worker_state.update(container=container, driver=driver, browser=browser)


def _teardown() -> None:
    for key, close in (
        ("browser", lambda b: b.close()),
        ("driver", lambda d: d.stop()),
        ("container", lambda c: c.remove(force=True)),
    ):
        obj = _worker_state.get(key)
        if obj is not None:
            try:
                close(obj)
            except Exception:
                pass
    _worker_state.clear()


def _ensure_browser():
    """Return a live browser, respawning the container if the CDP connection dropped."""
    browser = _worker_state.get("browser")
    if browser is not None and browser.is_connected():
        return browser
    _teardown()
    _spawn()
    return _worker_state["browser"]


def _render_once(browser, url: str) -> str:
    """Navigate url in a fresh context and return its HTML.

    Fresh context per job for isolation - cheaper than a new browser connection.
    """
    context = browser.new_context()
    try:
        page = context.new_page()
        page.goto(url, wait_until=NAV_WAIT_UNTIL, timeout=NAV_TIMEOUT)
        return page.content()
    finally:
        try:
            context.close()
        except Exception:
            pass


def update_job(job_id: str, **fields) -> None:
    """Set the given columns on a job row (sync, used from the Celery worker)."""
    with SyncSessionLocal() as session:
        job = session.get(Job, job_id)
        if job is not None:
            for key, value in fields.items():
                setattr(job, key, value)
            session.commit()


@celery.task(name=RENDER_TASK)
def render_task(job_id: str, url: str) -> None:
    """Render url and store the HTML (or error) on the job.

    A dropped CDP connection (dead browser) is retried once against a respawned browser.
    Other page errors fail directly.
    """
    for attempt in range(MAX_RENDER_ATTEMPTS):
        browser = _ensure_browser()
        try:
            html = _render_once(browser, url)
            update_job(job_id, status="done", html=html)
            return
        except PlaywrightTimeoutError:
            update_job(job_id, status="failed", error="Website timeout")
            return
        except Exception as exc:
            # Browser connection lost mid-render: respawn and retry once. Anything else
            # is a real page/render failure - record it.
            if not browser.is_connected() and attempt + 1 < MAX_RENDER_ATTEMPTS:
                continue
            update_job(job_id, status="failed", error=str(exc))
            return

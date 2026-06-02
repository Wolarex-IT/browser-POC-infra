from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .celery_app import celery
from .config import RENDER_TASK
from .db import AsyncSessionLocal, Base, async_engine
from .models import Job
from .schemas import JobCreated, JobStatusResponse, SubmitRequest


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Create the jobs table on startup and release the DB pool on shutdown."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()


app = FastAPI(lifespan=lifespan)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


@app.post("/", status_code=202, response_model=JobCreated)
async def submit_url(
    payload: SubmitRequest,
    session: AsyncSession = Depends(get_session),
) -> JobCreated:
    """Persist a pending job, enqueue it for rendering, and return its id.

    Returns immediately (202) - the actual navigation happens in a Celery worker, so
    the request never blocks on the browser.
    """
    job_id = str(uuid4())
    session.add(Job(id=job_id, status="pending"))
    await session.commit()

    # send_task enqueues by name so the app never imports the worker's browser code.
    # It is a blocking broker publish, so offload it to keep the event loop free.
    await run_in_threadpool(celery.send_task, RENDER_TASK, args=[job_id, str(payload.url)])

    return JobCreated(job_id=job_id)


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> JobStatusResponse:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(status=job.status, html=job.html, error=job.error)

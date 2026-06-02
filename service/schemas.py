from pydantic import BaseModel, HttpUrl


class SubmitRequest(BaseModel):
    url: HttpUrl


class JobCreated(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    status: str
    html: str | None = None
    error: str | None = None

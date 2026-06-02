# Quick browser POC (Proof of Concept)

The goal of the project is to quickly write a POC in the form of  a minimal FastAPI service that will accept a
website URL and return its rendered HTML using [CloakBrowser](https://github.com/CloakHQ/CloakBrowser).

## Usage

1. Build & Run FastAPI application and CloakBrowser using Docker Compose.
```bash
docker compose up -d
```

2. Test on `http://127.0.0.1:8000/docs` or via curl.

```bash
# submit a job, get back a job_id
curl -X POST "http://127.0.0.1:8000/" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'

# poll for the result
curl "http://127.0.0.1:8000/jobs/<job_id>"
```

### Available endpoints

- `POST /` - Submit `{"url": "..."}` for rendering. Returns `202` with `{"job_id": "..."}`.
The job is queued (Celery over RabbitMQ) and rendered by a worker, so the request never
blocks on navigation.
- `GET /jobs/{job_id}` - Poll a job (read from Postgres). Returns `{"status": "pending"}`,
`{"status": "done", "html": "..."}`, or `{"status": "failed", "error": "..."}`.
`404` if the job_id is unknown.

### Stack

- **app** - FastAPI (async SQLAlchemy + Pydantic). Enqueues jobs, serves polls.
- **worker** - Celery (sync Playwright). Spawns its own CloakBrowser container via the Docker
SDK per process, renders, writes the result to Postgres.
- **postgres** - durable job store (status / html / error) and Celery result backend.
- **rabbitmq** - Celery broker.

Celery task results live in Postgres (`db+...` backend) and expire after 7 days; the
worker runs with `--beat` so the periodic `backend_cleanup` purges them.

## Progress

Milestones, the achievement of which will help us better understand how to work with a browser:

- [x] Build a FastAPI app to use the CloakBrowser locally
- [x] Create a separate container with CloakBrowser and use it via the Playwright API over CDP
- [x] Create a container with CloakBrowser dynamically using the Docker SDK
- [ ] Cloudflare / bot-wall evasion (the hard part) - stealth browser patches and a
progressive escalation strategy to get past JS challenges and automation fingerprinting
- [ ] IP blocking resolution - proxy support with rotation across a pool so a banned IP
does not stop a crawl, geo-matched to the browser locale
- [ ] Header consistency (anti-fingerprint) - generate realistic user agents with matching
`Sec-CH-UA` client hints so headers never contradict each other

([DooD](https://www.google.com/search?q=Docker+outside+of+Docker))
